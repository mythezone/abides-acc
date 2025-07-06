from tqdm import tqdm
import heapq
from collections import defaultdict
from core.order import LimitOrder, MarketOrder, Order
from rich.table import Table
from rich.panel import Panel
import typing
from typing import List, Dict, Any, Optional, TYPE_CHECKING


class LimitOrderBook:
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.buy_heap = []  # max-heap: use -price
        self.sell_heap = []  # min-heap
        self.order_map = {}
        self.history_log = []

    def add_order(self, order: "Order"):
        trades = []

        if order.side == "buy":
            trades = self._match_order(order, self.sell_heap, "sell")
        elif order.side == "sell":
            trades = self._match_order(order, self.buy_heap, "buy")

        if order.quantity > 0 and isinstance(order, LimitOrder):
            self._insert_limit_order(order)

        self.history_log.extend(trades)
        return trades

    def _insert_limit_order(self, order: "LimitOrder"):
        order_entry = (
            order.price if order.side == "sell" else -order.price,
            order.timestamp,
            order.id,
            order,
        )
        if order.side == "buy":
            heapq.heappush(self.buy_heap, order_entry)
        else:
            heapq.heappush(self.sell_heap, order_entry)
        self.order_map[order.id] = order

    def _match_order(self, order, heap, opposing_side):
        trades = []
        while heap and order.quantity > 0:
            best_price, _, order_id, top_order = heap[0]

            if isinstance(order, LimitOrder) and isinstance(top_order, LimitOrder):
                if order.side == "buy" and order.price < top_order.price:
                    break
                if order.side == "sell" and order.price > -best_price:
                    break

            heapq.heappop(heap)
            traded_qty = min(order.quantity, top_order.quantity)
            trade_price = (
                top_order.price
                if hasattr(top_order, "price")
                else (order.price if hasattr(order, "price") else 0)
            )

            trades.append(
                {
                    "buy": (
                        order.agent_id if order.side == "buy" else top_order.agent_id
                    ),
                    "sell": (
                        top_order.agent_id if order.side == "buy" else order.agent_id
                    ),
                    "quantity": traded_qty,
                    "price": trade_price,
                    "timestamp": order.timestamp,
                    "symbol": self.symbol,
                }
            )

            order.quantity -= traded_qty
            top_order.quantity -= traded_qty

            if top_order.quantity > 0:
                heapq.heappush(
                    heap, (best_price, top_order.timestamp, order_id, top_order)
                )

        return trades

    def cancel_order(self, order_id):
        if order_id in self.order_map:
            del self.order_map[order_id]
            # Note: Actual heap cleanup not done here (for simplicity)

    def snapshot_top_n(self, n=5):
        def extract_top(heap, is_buy):
            sorted_heap = sorted(heap, reverse=is_buy)
            return [
                (abs(price), order.quantity) for price, _, _, order in sorted_heap[:n]
            ]

        return {
            "buy": extract_top(self.buy_heap, is_buy=True),
            "sell": extract_top(self.sell_heap, is_buy=False),
        }

    def render_lob(self):
        snapshot = self.snapshot_top_n(5)
        table = Table(title=f"{self.symbol} LOB - Top 5")
        table.add_column("买价", justify="right")
        table.add_column("买量", justify="right")
        table.add_column("卖价", justify="right")
        table.add_column("卖量", justify="right")

        for i in range(5):
            buy = snapshot["buy"][i] if i < len(snapshot["buy"]) else ("", "")
            sell = snapshot["sell"][i] if i < len(snapshot["sell"]) else ("", "")
            table.add_row(f"{buy[0]}", f"{buy[1]}", f"{sell[0]}", f"{sell[1]}")

        return Panel(table, title=f"{self.symbol} 限价订单簿")


# --- LOB performance test ---
import tracemalloc
import time
from core.order import generate_random_order


def test_lob_performance():
    lob = LimitOrderBook(symbol="TEST")
    tracemalloc.start()
    start_time = time.time()

    # for _ in tqdm(range(3000_000), desc="Processing Orders"):
    for _ in range(300_000):
        order = generate_random_order("TEST")
        lob.add_order(order)
        lob.render_lob()

    end_time = time.time()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    print(f"Processed 300,000 orders in {end_time - start_time:.2f} seconds")
    print(
        f"Current memory usage: {current / 1024 / 1024:.2f} MB; Peak: {peak / 1024 / 1024:.2f} MB"
    )


if __name__ == "__main__":
    test_lob_performance()
