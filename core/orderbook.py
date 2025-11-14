from __future__ import annotations

import csv
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Deque, Dict, Iterable, List, Optional, Tuple, Union

import pandas as pd

from core.order import LimitOrder, MarketOrder, Order


@dataclass
class OrderEntry:
    """Index entry tracking an order registered in the book."""

    order: LimitOrder
    side: str
    price: float


class PriceLevel:
    """FIFO queue of orders at a single price."""

    def __init__(self, price: float, side: str):
        self.price = float(price)
        self.side = side
        self.orders: Deque[LimitOrder] = deque()
        self.total_volume: int = 0

    def append(self, order: LimitOrder) -> None:
        self.orders.append(order)
        self.total_volume += int(order.quantity)

    def pop_front(self) -> LimitOrder:
        order = self.orders.popleft()
        self.total_volume -= int(order.quantity)
        return order

    def front(self) -> Optional[LimitOrder]:
        return self.orders[0] if self.orders else None

    def remove(self, order: LimitOrder) -> bool:
        for idx, existing in enumerate(self.orders):
            if existing is order:
                self.total_volume -= int(existing.quantity)
                del self.orders[idx]
                return True
        return False

    def empty(self) -> bool:
        return not self.orders


class LimitOrderBook:
    """Price/time priority book with behaviour aligned to MAXE's PriceTimeBook."""

    def __init__(self, stock: Optional[str]):
        self.stock = stock
        self.buy_prices: List[float] = []
        self.sell_prices: List[float] = []
        self.buy_levels: Dict[float, PriceLevel] = {}
        self.sell_levels: Dict[float, PriceLevel] = {}
        self._order_index: Dict[str, OrderEntry] = {}

        self.history_log: List[dict] = []
        self.last_trade_price: Optional[float] = None
        self.ohlc = {
            "open": None,
            "high": None,
            "low": None,
            "close": None,
            "volume": 0,
        }
        self.total_traded_volume: int = 0

    # ------------------------------------------------------------------ #
    # Public entry points
    # ------------------------------------------------------------------ #
    def add_order(self, order: Order) -> List[dict]:
        if order.side not in ("buy", "sell"):
            raise ValueError("order.side must be 'buy' or 'sell'")
        trades: List[dict] = []
        if isinstance(order, LimitOrder):
            trades = self._match_limit(order)
            if order.quantity > 0:
                self._rest(order)
        else:
            trades = self._match_market(order)
        self.history_log.extend(trades)
        return trades

    def cancel_order(self, order_id, quantity: Optional[int] = None) -> int:
        entry = self._order_index.get(order_id)
        if entry is None:
            return 0
        level = self._get_level(entry.price, entry.side)
        if level is None:
            self._order_index.pop(order_id, None)
            return 0
        order = entry.order
        remaining = int(order.quantity)
        if remaining <= 0:
            level.remove(order)
            self._order_index.pop(order_id, None)
            self._remove_level_if_empty(level)
            return 0
        if quantity is None or quantity >= remaining:
            level.remove(order)
            self._order_index.pop(order_id, None)
            self._remove_level_if_empty(level)
            return remaining
        removed = max(int(quantity), 0)
        order.quantity = remaining - removed
        level.total_volume -= removed
        if order.quantity <= 0:
            level.remove(order)
            self._order_index.pop(order_id, None)
            self._remove_level_if_empty(level)
            return remaining
        return removed

    def cancel_by_price(self, side: str, price: float, quantity: int) -> int:
        if quantity <= 0:
            return 0
        level = self._get_level(float(price), side)
        if level is None:
            return 0
        removed = 0
        while quantity > 0 and not level.empty():
            order = level.front()
            if order is None:
                break
            remaining = int(order.quantity)
            if remaining <= quantity:
                quantity -= remaining
                removed += remaining
                level.pop_front()
                self._order_index.pop(order.id, None)
            else:
                order.quantity = remaining - quantity
                removed += quantity
                level.total_volume -= quantity
                quantity = 0
        self._remove_level_if_empty(level)
        return removed

    def snapshot_top_n(self, n: int = 5) -> Dict[str, List[Tuple[float, int]]]:
        depth = max(int(n), 1)
        asks: List[Tuple[float, int]] = []
        bids: List[Tuple[float, int]] = []
        for price in self.sell_prices:
            level = self.sell_levels[price]
            vol = int(level.total_volume)
            if vol > 0:
                asks.append((price, vol))
            if len(asks) >= depth:
                break
        for price in reversed(self.buy_prices):
            level = self.buy_levels[price]
            vol = int(level.total_volume)
            if vol > 0:
                bids.append((price, vol))
            if len(bids) >= depth:
                break
        return {"sell": asks, "buy": bids}

    def format_snapshot_csv(self, n: int = 5) -> str:
        snap = self.snapshot_top_n(n)
        parts: List[str] = []
        asks = snap["sell"]
        bids = snap["buy"]
        for i in range(n):
            parts.append(f"{asks[i][0]:.2f}" if i < len(asks) else "")
        for i in range(n):
            parts.append(str(asks[i][1]) if i < len(asks) else "")
        for i in range(n):
            parts.append(f"{bids[i][0]:.2f}" if i < len(bids) else "")
        for i in range(n):
            parts.append(str(bids[i][1]) if i < len(bids) else "")
        return ",".join(parts)

    def initialize_from_snapshot(
        self,
        bids: Iterable[Tuple[float, int]],
        asks: Iterable[Tuple[float, int]],
        *,
        agent_id: str = "InitAgent",
        timestamp: str = "1970-01-01T00:00:00",
    ) -> None:
        ts = pd.Timestamp(timestamp)
        for price, volume in bids:
            volume = int(volume)
            if volume <= 0:
                continue
            order = LimitOrder(
                agent_id=agent_id,
                timestamp=str(ts),
                side="buy",
                quantity=volume,
                price=float(price),
                stock=self.stock or "",
                id=f"INIT_BID_{price}_{volume}",
            )
            self.add_order(order)
        for price, volume in asks:
            volume = int(volume)
            if volume <= 0:
                continue
            order = LimitOrder(
                agent_id=agent_id,
                timestamp=str(ts),
                side="sell",
                quantity=volume,
                price=float(price),
                stock=self.stock or "",
                id=f"INIT_ASK_{price}_{volume}",
            )
            self.add_order(order)

    def initialize_from_csv(
        self,
        path: Union[str, Path],
        *,
        agent_id: str = "InitAgent",
        timestamp: str = "1970-01-01T00:00:00",
    ) -> None:
        bids: List[Tuple[float, int]] = []
        asks: List[Tuple[float, int]] = []
        with open(path, "r", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    bid_price = float(row.get("bid_price"))
                    bid_volume = int(float(row.get("bid_volume", 0)))
                except (TypeError, ValueError):
                    bid_volume = 0
                else:
                    if bid_volume > 0:
                        bids.append((bid_price, bid_volume))
                try:
                    ask_price = float(row.get("ask_price"))
                    ask_volume = int(float(row.get("ask_volume", 0)))
                except (TypeError, ValueError):
                    ask_volume = 0
                else:
                    if ask_volume > 0:
                        asks.append((ask_price, ask_volume))
        if bids or asks:
            self.initialize_from_snapshot(
                bids=bids,
                asks=asks,
                agent_id=agent_id,
                timestamp=timestamp,
            )

    def reset_ohlc(self) -> None:
        close = self.ohlc["close"]
        self.ohlc = {
            "open": close,
            "high": close,
            "low": close,
            "close": close,
            "volume": 0,
        }

    def render_lob(self) -> str:
        snap = self.snapshot_top_n(5)
        lines = [f"Order Book for {self.stock or 'UNKNOWN'}"]
        lines.append(" Side | Price | Volume")
        for price, qty in snap["sell"]:
            lines.append(f"  ASK | {price:>8.2f} | {qty:>6}")
        lines.append("  ---   ------   ------")
        for price, qty in snap["buy"]:
            lines.append(f"  BID | {price:>8.2f} | {qty:>6}")
        return "\n".join(lines)

    @property
    def order_map(self) -> Dict[str, OrderEntry]:
        return self._order_index

    def traded_volume(self) -> int:
        return int(self.total_traded_volume)

    def resting_volume(self, side: str, depth: Optional[int] = None) -> int:
        depth = int(depth) if depth is not None else None
        prices = (
            list(reversed(self.buy_prices)) if side == "buy" else list(self.sell_prices)
        )
        total = 0
        for idx, price in enumerate(prices):
            level = self._get_level(price, side)
            if not level:
                continue
            total += int(level.total_volume)
            if depth is not None and idx + 1 >= depth:
                break
        return total

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _get_level(self, price: float, side: str) -> Optional[PriceLevel]:
        if side == "buy":
            return self.buy_levels.get(price)
        return self.sell_levels.get(price)

    def _ensure_level(self, price: float, side: str) -> PriceLevel:
        level = self._get_level(price, side)
        if level is not None:
            return level
        level = PriceLevel(price, side)
        if side == "buy":
            self.buy_levels[price] = level
            self._insert_price(self.buy_prices, price)
        else:
            self.sell_levels[price] = level
            self._insert_price(self.sell_prices, price)
        return level

    @staticmethod
    def _insert_price(prices: List[float], price: float) -> None:
        from bisect import bisect_left

        idx = bisect_left(prices, price)
        if idx >= len(prices) or prices[idx] != price:
            prices.insert(idx, price)

    def _remove_level_if_empty(self, level: PriceLevel) -> None:
        if not level.empty():
            return
        price = level.price
        if level.side == "buy":
            self.buy_levels.pop(price, None)
            try:
                self.buy_prices.remove(price)
            except ValueError:
                pass
        else:
            self.sell_levels.pop(price, None)
            try:
                self.sell_prices.remove(price)
            except ValueError:
                pass

    def _best_buy_price(self) -> Optional[float]:
        return self.buy_prices[-1] if self.buy_prices else None

    def _best_sell_price(self) -> Optional[float]:
        return self.sell_prices[0] if self.sell_prices else None

    def _match_limit(self, order: LimitOrder) -> List[dict]:
        trades: List[dict] = []
        if order.side == "buy":
            while order.quantity > 0:
                best_price = self._best_sell_price()
                if best_price is None or best_price > order.price:
                    break
                level = self.sell_levels[best_price]
                trades.extend(self._consume_level(order, level, "sell"))
                self._remove_level_if_empty(level)
        else:
            while order.quantity > 0:
                best_price = self._best_buy_price()
                if best_price is None or best_price < order.price:
                    break
                level = self.buy_levels[best_price]
                trades.extend(self._consume_level(order, level, "buy"))
                self._remove_level_if_empty(level)
        return trades

    def _match_market(self, order: MarketOrder) -> List[dict]:
        trades: List[dict] = []
        levels_remaining = (
            int(order.market_depth) if order.market_depth is not None else None
        )
        if order.side == "buy":
            while order.quantity > 0:
                best_price = self._best_sell_price()
                if best_price is None:
                    break
                if levels_remaining is not None:
                    if levels_remaining <= 0:
                        break
                    levels_remaining -= 1
                level = self.sell_levels[best_price]
                trades.extend(self._consume_level(order, level, "sell"))
                self._remove_level_if_empty(level)
                if levels_remaining is not None and order.quantity > 0:
                    continue
        else:
            while order.quantity > 0:
                best_price = self._best_buy_price()
                if best_price is None:
                    break
                if levels_remaining is not None:
                    if levels_remaining <= 0:
                        break
                    levels_remaining -= 1
                level = self.buy_levels[best_price]
                trades.extend(self._consume_level(order, level, "buy"))
                self._remove_level_if_empty(level)
                if levels_remaining is not None and order.quantity > 0:
                    continue
        return trades

    def _consume_level(
        self, incoming: Order, level: PriceLevel, opposing_side: str
    ) -> List[dict]:
        trades: List[dict] = []
        while incoming.quantity > 0 and not level.empty():
            resting = level.front()
            if resting is None:
                break
            traded_qty = min(int(incoming.quantity), int(resting.quantity))
            incoming.quantity -= traded_qty
            resting.quantity -= traded_qty
            level.total_volume -= traded_qty

            buyer = incoming.agent_id if incoming.side == "buy" else resting.agent_id
            seller = resting.agent_id if incoming.side == "buy" else incoming.agent_id
            trade = {
                "stock": self.stock,
                "price": round(float(level.price), 6),
                "quantity": int(traded_qty),
                "timestamp": self._normalize_time(incoming.timestamp),
                "buy": buyer,
                "sell": seller,
            }
            trades.append(trade)
            self._record_trade(trade)

            if resting.quantity <= 0:
                level.pop_front()
                self._order_index.pop(resting.id, None)
            if incoming.quantity <= 0:
                break
        return trades

    def _rest(self, order: LimitOrder) -> None:
        level = self._ensure_level(float(order.price), order.side)
        level.append(order)
        self._order_index[order.id] = OrderEntry(
            order=order,
            side=order.side,
            price=float(order.price),
        )

    def _record_trade(self, trade: dict) -> None:
        price = float(trade["price"])
        qty = int(trade["quantity"])
        self.last_trade_price = price
        if self.ohlc["open"] is None:
            self.ohlc["open"] = price
            self.ohlc["high"] = price
            self.ohlc["low"] = price
        self.ohlc["close"] = price
        self.ohlc["high"] = max(self.ohlc["high"], price)
        self.ohlc["low"] = min(self.ohlc["low"], price)
        self.ohlc["volume"] += qty
        self.total_traded_volume += qty

    @staticmethod
    def _normalize_time(ts) -> str:
        try:
            return str(pd.Timestamp(ts))
        except Exception:
            return str(ts)
