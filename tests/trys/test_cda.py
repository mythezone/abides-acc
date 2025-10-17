from __future__ import annotations

import csv
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Deque, Dict, Iterable, List, Optional, Tuple

import pandas as pd


# ---------------------------------------------------------------------------
# Order primitives
# ---------------------------------------------------------------------------


@dataclass
class Order:
    id: str
    side: str  # 'buy' or 'sell'
    quantity: int
    timestamp: pd.Timestamp
    symbol: str = ""
    original_quantity: int = field(init=False)

    def __post_init__(self) -> None:
        self.original_quantity = int(self.quantity)


@dataclass
class LimitOrder(Order):
    price: float = 0.0


@dataclass
class MarketOrder(Order):
    market_depth: Optional[int] = None


# ---------------------------------------------------------------------------
# Order book in the spirit of MAXE PriceTimeBook
# ---------------------------------------------------------------------------


class PriceLevel:
    def __init__(self, price: float) -> None:
        self.price = float(price)
        self.orders: Deque[LimitOrder] = deque()

    def append(self, order: LimitOrder) -> None:
        self.orders.append(order)

    def pop_front(self) -> LimitOrder:
        return self.orders.popleft()

    def front(self) -> Optional[LimitOrder]:
        return self.orders[0] if self.orders else None

    def remove_order(self, target: LimitOrder) -> None:
        for idx, order in enumerate(self.orders):
            if order is target:
                del self.orders[idx]
                break

    def empty(self) -> bool:
        return not self.orders

    def total_quantity(self) -> int:
        return sum(int(o.quantity) for o in self.orders)


class TestOrderBook:
    def __init__(self, symbol: str = "") -> None:
        self.symbol = symbol
        self.buy_prices: List[float] = []
        self.sell_prices: List[float] = []
        self.buy_levels: Dict[float, PriceLevel] = {}
        self.sell_levels: Dict[float, PriceLevel] = {}
        self.orders_by_id: Dict[str, Tuple[str, float, LimitOrder]] = {}
        self.trade_log: List[Dict[str, object]] = []
        self.trade_counter = 0

    # ---- helpers ---------------------------------------------------------

    @staticmethod
    def _insert_price(prices: List[float], price: float) -> None:
        """Insert price keeping list sorted ascending."""
        from bisect import bisect_left

        idx = bisect_left(prices, price)
        if idx >= len(prices) or prices[idx] != price:
            prices.insert(idx, price)

    @staticmethod
    def _remove_price(prices: List[float], price: float) -> None:
        try:
            prices.remove(price)
        except ValueError:
            pass

    def _best_buy_price(self) -> Optional[float]:
        return self.buy_prices[-1] if self.buy_prices else None

    def _best_sell_price(self) -> Optional[float]:
        return self.sell_prices[0] if self.sell_prices else None

    def _ensure_level(self, price: float, side: str) -> PriceLevel:
        if side == "buy":
            level = self.buy_levels.get(price)
            if level is None:
                level = PriceLevel(price)
                self.buy_levels[price] = level
                self._insert_price(self.buy_prices, price)
            return level
        level = self.sell_levels.get(price)
        if level is None:
            level = PriceLevel(price)
            self.sell_levels[price] = level
            self._insert_price(self.sell_prices, price)
        return level

    def _remove_level_if_empty(self, level: PriceLevel, side: str) -> None:
        if not level.empty():
            return
        if side == "buy":
            self.buy_levels.pop(level.price, None)
            self._remove_price(self.buy_prices, level.price)
        else:
            self.sell_levels.pop(level.price, None)
            self._remove_price(self.sell_prices, level.price)

    # ---- public API ------------------------------------------------------

    def initialize_from_snapshot(self, snapshot: Iterable[Tuple[float, int, float, int]], timestamp: pd.Timestamp) -> None:
        """
        Initialize with iterable of (bid_price, bid_volume, ask_price, ask_volume)
        """
        for idx, (bid_price, bid_volume, ask_price, ask_volume) in enumerate(snapshot):
            if bid_volume > 0:
                order = LimitOrder(
                    id=f"INIT_BID_{idx}",
                    side="buy",
                    quantity=int(bid_volume),
                    price=float(bid_price),
                    timestamp=timestamp,
                    symbol=self.symbol,
                )
                self.add_limit_order(order, timestamp)
            if ask_volume > 0:
                order = LimitOrder(
                    id=f"INIT_ASK_{idx}",
                    side="sell",
                    quantity=int(ask_volume),
                    price=float(ask_price),
                    timestamp=timestamp,
                    symbol=self.symbol,
                )
                self.add_limit_order(order, timestamp)

    # ---- order entry -----------------------------------------------------

    def add_limit_order(self, order: LimitOrder, timestamp: pd.Timestamp) -> None:
        # cancel existing order with same id if necessary
        if order.id in self.orders_by_id:
            self.cancel_order(order.id, None)

        if order.side == "buy":
            self._match_buy(order, timestamp)
            if order.quantity > 0:
                level = self._ensure_level(order.price, "buy")
                level.append(order)
                self.orders_by_id[order.id] = ("buy", order.price, order)
        else:
            self._match_sell(order, timestamp)
            if order.quantity > 0:
                level = self._ensure_level(order.price, "sell")
                level.append(order)
                self.orders_by_id[order.id] = ("sell", order.price, order)

    def add_market_order(self, order: MarketOrder, timestamp: pd.Timestamp) -> None:
        if order.side == "buy":
            levels_remaining = order.market_depth
            while order.quantity > 0:
                best_price = self._best_sell_price()
                if best_price is None:
                    break
                if levels_remaining is not None:
                    if levels_remaining <= 0:
                        break
                    levels_remaining -= 1
                level = self.sell_levels[best_price]
                self._consume_level(order, level, "sell", timestamp)
                self._remove_level_if_empty(level, "sell")
                if levels_remaining is not None and order.quantity > 0:
                    continue
        else:
            levels_remaining = order.market_depth
            while order.quantity > 0:
                best_price = self._best_buy_price()
                if best_price is None:
                    break
                if levels_remaining is not None:
                    if levels_remaining <= 0:
                        break
                    levels_remaining -= 1
                level = self.buy_levels[best_price]
                self._consume_level(order, level, "buy", timestamp)
                self._remove_level_if_empty(level, "buy")
                if levels_remaining is not None and order.quantity > 0:
                    continue

    # ---- cancellation ----------------------------------------------------

    def cancel_order(self, order_id: str, quantity: Optional[int]) -> int:
        entry = self.orders_by_id.get(order_id)
        if entry is None:
            return 0
        side, price, order = entry
        level = self.buy_levels.get(price) if side == "buy" else self.sell_levels.get(price)
        if level is None:
            self.orders_by_id.pop(order_id, None)
            return 0
        remaining = int(order.quantity)
        if quantity is None or quantity >= remaining:
            level.remove_order(order)
            self.orders_by_id.pop(order_id, None)
            self._remove_level_if_empty(level, side)
            return remaining
        removed = int(quantity)
        order.quantity = remaining - removed
        if order.quantity <= 0:
            level.remove_order(order)
            self.orders_by_id.pop(order_id, None)
            self._remove_level_if_empty(level, side)
            return remaining
        return removed

    # ---- matching internals ----------------------------------------------

    def _match_buy(self, order: LimitOrder, timestamp: pd.Timestamp) -> None:
        while order.quantity > 0:
            best_price = self._best_sell_price()
            if best_price is None or best_price > order.price:
                break
            level = self.sell_levels[best_price]
            self._consume_level(order, level, "sell", timestamp)
            self._remove_level_if_empty(level, "sell")

    def _match_sell(self, order: LimitOrder, timestamp: pd.Timestamp) -> None:
        while order.quantity > 0:
            best_price = self._best_buy_price()
            if best_price is None or best_price < order.price:
                break
            level = self.buy_levels[best_price]
            self._consume_level(order, level, "buy", timestamp)
            self._remove_level_if_empty(level, "buy")

    def _consume_level(self, incoming: Order, level: PriceLevel, side: str, timestamp: pd.Timestamp) -> None:
        while incoming.quantity > 0 and not level.empty():
            resting = level.front()
            if resting is None:
                break
            traded_qty = min(int(incoming.quantity), int(resting.quantity))
            incoming.quantity -= traded_qty
            resting.quantity -= traded_qty
            self._record_trade(
                price=level.price,
                quantity=traded_qty,
                timestamp=timestamp,
            )
            if resting.quantity <= 0:
                filled = level.pop_front()
                self.orders_by_id.pop(filled.id, None)
            if incoming.quantity <= 0:
                break

    def _record_trade(self, price: float, quantity: int, timestamp: pd.Timestamp) -> None:
        self.trade_counter += 1
        self.trade_log.append(
            {
                "id": self.trade_counter,
                "timestamp": timestamp,
                "price": float(price),
                "volume": int(quantity),
            }
        )

    # ---- analytics -------------------------------------------------------

    def snapshot(self, depth: int) -> Dict[str, List[Tuple[float, int]]]:
        depth = max(int(depth), 1)
        asks: List[Tuple[float, int]] = []
        bids: List[Tuple[float, int]] = []

        for price in self.sell_prices:
            level = self.sell_levels[price]
            qty = level.total_quantity()
            if qty > 0:
                asks.append((price, qty))
            if len(asks) >= depth:
                break

        for price in reversed(self.buy_prices):
            level = self.buy_levels[price]
            qty = level.total_quantity()
            if qty > 0:
                bids.append((price, qty))
            if len(bids) >= depth:
                break

        return {"asks": asks, "bids": bids}

    def best_quotes(self) -> Tuple[Optional[Tuple[float, int]], Optional[Tuple[float, int]]]:
        best_ask_price = self._best_sell_price()
        best_bid_price = self._best_buy_price()
        best_ask = None
        best_bid = None
        if best_ask_price is not None:
            level = self.sell_levels[best_ask_price]
            best_ask = (best_ask_price, level.total_quantity())
        if best_bid_price is not None:
            level = self.buy_levels[best_bid_price]
            best_bid = (best_bid_price, level.total_quantity())
        return best_bid, best_ask


# ---------------------------------------------------------------------------
# Replay driver
# ---------------------------------------------------------------------------


def _load_snapshot_csv(path: Path) -> List[Tuple[float, int, float, int]]:
    rows: List[Tuple[float, int, float, int]] = []
    with path.open("r", newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for line in reader:
            try:
                bid_price = float(line.get("bid_price", 0.0))
                bid_volume = int(float(line.get("bid_volume", 0)))
            except (TypeError, ValueError):
                bid_volume = 0
                bid_price = 0.0
            try:
                ask_price = float(line.get("ask_price", 0.0))
                ask_volume = int(float(line.get("ask_volume", 0)))
            except (TypeError, ValueError):
                ask_price = 0.0
                ask_volume = 0
            rows.append((bid_price, bid_volume, ask_price, ask_volume))
    return rows


def _parse_side(flag) -> str:
    return "buy" if str(flag) in {"1", "BUY", "buy"} else "sell"


def _parse_order_type(value) -> str:
    return "market" if str(value).strip() == "1" else "limit"


def replay_orders(
    orders_csv: Path,
    *,
    snapshot_csv: Optional[Path] = None,
    depth: int = 5,
    snapshot_interval: pd.Timedelta = pd.Timedelta(seconds=3),
    cancel_flag: int = 2,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    orders_path = Path(orders_csv)
    if not orders_path.exists():
        raise FileNotFoundError(f"Orders CSV not found: {orders_csv}")
    df = pd.read_csv(orders_path)
    if df.empty:
        raise ValueError("Orders CSV is empty.")

    if "SIMUTIME" in df.columns and df["SIMUTIME"].notna().any():
        get_time = lambda row, base: base + pd.to_timedelta(float(row["SIMUTIME"]), unit="s")
        base_time = pd.Timestamp(df.iloc[0]["TIMESTAMP"])
    else:
        get_time = lambda row, base: pd.Timestamp(row["TIMESTAMP"])
        base_time = pd.Timestamp(df.iloc[0]["TIMESTAMP"])

    book = TestOrderBook()
    if snapshot_csv:
        snapshot_path = Path(snapshot_csv)
        if not snapshot_path.exists():
            raise FileNotFoundError(f"Snapshot CSV not found: {snapshot_csv}")
        snapshot_rows = _load_snapshot_csv(snapshot_path)
        book.initialize_from_snapshot(snapshot_rows, base_time)

    trades: List[Dict[str, object]] = []
    snapshots: List[Dict[str, object]] = []
    next_snapshot_time = base_time + snapshot_interval

    for _, row in df.iterrows():
        event_time = get_time(row, base_time)
        symbol = row.get("SYMBOL") or ""

        # record snapshots up to current event time
        while event_time >= next_snapshot_time:
            snapshots.append(
                _snapshot_record(
                    book,
                    next_snapshot_time,
                    base_time,
                    depth,
                )
            )
            next_snapshot_time += snapshot_interval

        cancel_type_raw = row.get("CANCEL_TYPE")
        try:
            cancel_type = int(cancel_type_raw)
        except Exception:
            cancel_type = None

        raw_order_id = row.get("ORDER_ID")
        order_id = str(raw_order_id).strip() if pd.notna(raw_order_id) else None
        size_val = row.get("SIZE", 0)
        try:
            size = int(float(size_val))
        except Exception:
            size = 0
        if cancel_type == cancel_flag and order_id:
            cancelled = book.cancel_order(order_id, size if size > 0 else None)
            if cancelled:
                trades.extend(_format_trades(book.trade_log, base_time))
                book.trade_log.clear()
            continue

        if size <= 0:
            continue

        side = _parse_side(row.get("BUY_SELL_FLAG"))
        order_type = _parse_order_type(row.get("ORDER_TYPE", "2"))
        if order_type == "market":
            order = MarketOrder(
                id=order_id or f"MKT_{event_time.value}",
                side=side,
                quantity=size,
                timestamp=event_time,
                symbol=symbol,
                market_depth=None,
            )
            book.add_market_order(order, event_time)
        else:
            price_val = row.get("PRICE")
            if pd.isna(price_val):
                continue
            try:
                price = float(price_val)
            except Exception:
                continue
            order = LimitOrder(
                id=order_id or f"LMT_{event_time.value}",
                side=side,
                quantity=size,
                price=price,
                timestamp=event_time,
                symbol=symbol,
            )
            book.add_limit_order(order, event_time)

        if book.trade_log:
            trades.extend(_format_trades(book.trade_log, base_time))
            book.trade_log.clear()

    # final snapshots up to last event time
    final_time = get_time(df.iloc[-1], base_time)
    while next_snapshot_time <= final_time:
        snapshots.append(
            _snapshot_record(
                book,
                next_snapshot_time,
                base_time,
                depth,
            )
        )
        next_snapshot_time += snapshot_interval

    trades_df = pd.DataFrame(trades, columns=["id", "time", "volume", "price"])
    snapshot_columns = ["time", "mid_price"]
    for level in range(depth):
        snapshot_columns.extend(
            [
                f"ask_price_{level+1}",
                f"ask_volume_{level+1}",
                f"bid_price_{level+1}",
                f"bid_volume_{level+1}",
            ]
        )
    snapshots_df = pd.DataFrame(snapshots, columns=snapshot_columns)
    return trades_df, snapshots_df


def _format_trades(trades: List[Dict[str, object]], base_time: pd.Timestamp) -> List[Dict[str, object]]:
    formatted: List[Dict[str, object]] = []
    for item in trades:
        rel_time = (pd.Timestamp(item["timestamp"]) - base_time).total_seconds()
        formatted.append(
            {
                "id": item["id"],
                "time": round(rel_time, 6),
                "volume": float(item["volume"]),
                "price": float(item["price"]),
            }
        )
    return formatted


def _snapshot_record(
    book: TestOrderBook,
    snapshot_time: pd.Timestamp,
    base_time: pd.Timestamp,
    depth: int,
) -> Dict[str, object]:
    rel = (snapshot_time - base_time).total_seconds()
    best_bid, best_ask = book.best_quotes()
    if best_bid and best_ask:
        mid = (best_bid[0] + best_ask[0]) / 2.0
    else:
        mid = None
    snapshot = book.snapshot(depth)
    record: Dict[str, object] = {"time": round(rel, 6), "mid_price": mid if mid is not None else ""}
    asks = snapshot["asks"]
    bids = snapshot["bids"]
    for idx in range(depth):
        if idx < len(asks):
            record[f"ask_price_{idx+1}"] = asks[idx][0]
            record[f"ask_volume_{idx+1}"] = asks[idx][1]
        else:
            record[f"ask_price_{idx+1}"] = ""
            record[f"ask_volume_{idx+1}"] = ""
        if idx < len(bids):
            record[f"bid_price_{idx+1}"] = bids[idx][0]
            record[f"bid_volume_{idx+1}"] = bids[idx][1]
        else:
            record[f"bid_price_{idx+1}"] = ""
            record[f"bid_volume_{idx+1}"] = ""
    return record
