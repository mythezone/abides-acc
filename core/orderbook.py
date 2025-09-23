from __future__ import annotations

import heapq
import itertools
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple
import csv
from pathlib import Path

import pandas as pd

from core.order import LimitOrder, MarketOrder, Order


@dataclass
class OrderNode:
    """Linked-list node wrapping an order stored at a price level."""

    order: LimitOrder
    prev: Optional["OrderNode"] = None
    next: Optional["OrderNode"] = None
    level: Optional["PriceLevel"] = None


class PriceLevel:
    """FIFO queue of orders at a single price."""

    __slots__ = ("price", "side", "head", "tail", "total_quantity", "active")

    def __init__(self, price: float, side: str):
        self.price = float(price)
        self.side = side  # 'buy' or 'sell'
        self.head: Optional[OrderNode] = None
        self.tail: Optional[OrderNode] = None
        self.total_quantity: int = 0
        self.active: bool = True

    def append(self, node: OrderNode) -> None:
        node.prev = self.tail
        node.next = None
        node.level = self
        if self.tail:
            self.tail.next = node
            self.tail = node
        else:
            self.head = self.tail = node
        self.total_quantity += int(node.order.quantity)

    def remove(self, node: OrderNode) -> None:
        if node.prev:
            node.prev.next = node.next
        else:
            self.head = node.next
        if node.next:
            node.next.prev = node.prev
        else:
            self.tail = node.prev
        self.total_quantity -= int(node.order.quantity)
        node.prev = node.next = None
        node.level = None

    def consume_from_head(self, quantity: int) -> OrderNode:
        node = self.head
        if node is None:
            raise RuntimeError("Attempted to consume from an empty price level")
        node.order.quantity -= quantity
        self.total_quantity -= quantity
        if node.order.quantity <= 0:
            node.order.quantity = 0
            self.remove(node)
        return node

    def top_node(self) -> Optional[OrderNode]:
        return self.head

    def is_empty(self) -> bool:
        return self.head is None


class OrderHeap:
    """Heap of price levels maintaining best price first."""

    def __init__(self, side: str):
        if side not in ("buy", "sell"):
            raise ValueError("side must be 'buy' or 'sell'")
        self.side = side
        self._heap: List[Tuple[float, int, PriceLevel]] = []
        self._price_map: Dict[float, PriceLevel] = {}
        self._counter = itertools.count()

    def _heap_price(self, price: float) -> float:
        return -price if self.side == "buy" else price

    def ensure_level(self, price: float) -> PriceLevel:
        level = self._price_map.get(price)
        if level is None or not level.active:
            level = PriceLevel(price, self.side)
            self._price_map[price] = level
            heapq.heappush(self._heap, (self._heap_price(price), next(self._counter), level))
        return level

    def best_level(self) -> Optional[PriceLevel]:
        while self._heap:
            _, _, level = self._heap[0]
            if level.active and not level.is_empty():
                return level
            heapq.heappop(self._heap)
            if level.price in self._price_map and (not level.active or level.is_empty()):
                self._price_map.pop(level.price, None)
        return None

    def remove_level(self, level: PriceLevel) -> None:
        level.active = False
        self._price_map.pop(level.price, None)

    def prices(self) -> Iterable[float]:
        return list(self._price_map.keys())

    def get_level(self, price: float) -> Optional[PriceLevel]:
        level = self._price_map.get(price)
        if level and level.active and not level.is_empty():
            return level
        return None


class LimitOrderBook:
    """Price-level order book with FIFO queues per price and heap-based best-price access."""

    def __init__(self, symbol: Optional[str]):
        self.symbol = symbol
        self.bids = OrderHeap("buy")
        self.asks = OrderHeap("sell")
        self._order_index: Dict[str, OrderNode] = {}
        self.history_log: List[dict] = []
        self.last_trade_price: Optional[float] = None
        self.ohlc = {
            "open": None,
            "high": None,
            "low": None,
            "close": None,
            "volume": 0,
        }

    # --- Public API ---
    def add_order(self, order: Order) -> List[dict]:
        if order.side not in ("buy", "sell"):
            raise ValueError("order.side must be 'buy' or 'sell'")
        trades = self._match(order)
        if isinstance(order, LimitOrder) and order.quantity > 0:
            self._rest(order)
        self.history_log.extend(trades)
        return trades

    def cancel_order(self, order_id) -> bool:
        node = self._order_index.pop(order_id, None)
        if not node:
            return False
        level = node.level
        if level:
            level.remove(node)
            if level.is_empty():
                heap = self.bids if level.side == "buy" else self.asks
                heap.remove_level(level)
        return True

    def cancel_by_price(self, side: str, price: float, quantity: int) -> int:
        if quantity <= 0:
            return 0
        heap = self.bids if side == "buy" else self.asks
        level = heap.get_level(float(price))
        if level is None:
            return 0
        removed = 0
        while quantity > 0:
            node = level.top_node()
            if node is None:
                heap.remove_level(level)
                break
            remaining = int(node.order.quantity)
            if remaining <= quantity:
                quantity -= remaining
                removed += remaining
                level.remove(node)
                self._order_index.pop(node.order.id, None)
            else:
                node.order.quantity -= quantity
                level.total_quantity -= quantity
                removed += quantity
                quantity = 0
        if level.is_empty():
            heap.remove_level(level)
        return removed

    def snapshot_top_n(self, n: int = 5) -> Dict[str, List[Tuple[float, int]]]:
        top_buys = self._top_levels(self.bids, n, reverse=True)
        top_sells = self._top_levels(self.asks, n, reverse=False)
        return {"buy": top_buys, "sell": top_sells}

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
        for price, volume in bids:
            if volume <= 0:
                continue
            order = LimitOrder(
                agent_id=agent_id,
                timestamp=timestamp,
                side="buy",
                quantity=int(volume),
                price=float(price),
                id=f"init_bid_{self.symbol}_{price}_{volume}",
            )
            self._rest(order)
        for price, volume in asks:
            if volume <= 0:
                continue
            order = LimitOrder(
                agent_id=agent_id,
                timestamp=timestamp,
                side="sell",
                quantity=int(volume),
                price=float(price),
                id=f"init_ask_{self.symbol}_{price}_{volume}",
            )
            self._rest(order)

    def initialize_from_csv(
        self,
        path: str | Path,
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
                    bid_volume = int(row.get("bid_volume", 0))
                except (TypeError, ValueError):
                    bid_volume = 0
                else:
                    if bid_volume > 0:
                        bids.append((bid_price, bid_volume))
                try:
                    ask_price = float(row.get("ask_price"))
                    ask_volume = int(row.get("ask_volume", 0))
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
        lines = [f"Order Book for {self.symbol or 'UNKNOWN'}"]
        lines.append(" Side | Price | Volume")
        for price, qty in snap["sell"]:
            lines.append(f"  ASK | {price:>8.2f} | {qty:>6}")
        lines.append("  ---   ------   ------")
        for price, qty in snap["buy"]:
            lines.append(f"  BID | {price:>8.2f} | {qty:>6}")
        return "\n".join(lines)

    @property
    def order_map(self) -> Dict[str, OrderNode]:
        return self._order_index

    # --- Internal helpers ---
    def _match(self, incoming: Order) -> List[dict]:
        trades: List[dict] = []
        opposite = self.asks if incoming.side == "buy" else self.bids
        market_depth: Optional[int] = None
        if isinstance(incoming, MarketOrder):
            market_depth = incoming.market_depth if incoming.market_depth else None
        levels_remaining = market_depth
        active_price = None

        while incoming.quantity > 0:
            level = opposite.best_level()
            if not level:
                break
            best_price = level.price

            if isinstance(incoming, LimitOrder):
                if incoming.side == "buy" and incoming.price < best_price:
                    break
                if incoming.side == "sell" and incoming.price > best_price:
                    break

            if levels_remaining is not None:
                if active_price is None or best_price != active_price:
                    if levels_remaining <= 0:
                        break
                    active_price = best_price
                    levels_remaining -= 1

            head = level.top_node()
            if head is None:
                opposite.remove_level(level)
                active_price = None
                continue

            resting = head.order
            traded_qty = min(incoming.quantity, resting.quantity)
            trade_price = best_price
            trade_time = self._normalize_time(incoming.timestamp)

            buyer = incoming.agent_id if incoming.side == "buy" else resting.agent_id
            seller = resting.agent_id if incoming.side == "buy" else incoming.agent_id

            trade = {
                "symbol": self.symbol,
                "price": round(float(trade_price), 6),
                "quantity": int(traded_qty),
                "timestamp": trade_time,
                "buy": buyer,
                "sell": seller,
            }
            trades.append(trade)
            self._record_trade(trade)

            incoming.quantity -= traded_qty
            level.consume_from_head(traded_qty)

            if resting.quantity == 0:
                self._order_index.pop(resting.id, None)

            if level.is_empty():
                opposite.remove_level(level)
                active_price = None

        return trades

    def _rest(self, order: LimitOrder) -> None:
        heap = self.bids if order.side == "buy" else self.asks
        level = heap.ensure_level(order.price)
        node = OrderNode(order=order)
        level.append(node)
        self._order_index[order.id] = node

    def _top_levels(self, heap: OrderHeap, n: int, *, reverse: bool) -> List[Tuple[float, int]]:
        prices = sorted(heap.prices(), reverse=reverse)
        result: List[Tuple[float, int]] = []
        for price in prices:
            level = heap.get_level(price)
            if not level:
                continue
            qty = level.total_quantity
            if qty > 0:
                result.append((price, qty))
            if len(result) >= n:
                break
        return result

    def _record_trade(self, trade: dict) -> None:
        price = trade["price"]
        qty = trade["quantity"]
        self.last_trade_price = price
        if self.ohlc["open"] is None:
            self.ohlc["open"] = price
            self.ohlc["high"] = price
            self.ohlc["low"] = price
        self.ohlc["close"] = price
        self.ohlc["high"] = max(self.ohlc["high"], price)
        self.ohlc["low"] = min(self.ohlc["low"], price)
        self.ohlc["volume"] += qty

    @staticmethod
    def _normalize_time(ts) -> str:
        try:
            return str(pd.Timestamp(ts))
        except Exception:
            return str(ts)
