# LimitOrder class, inherits from Order class, adds a limit price.  These are the
# Orders that typically go in an Exchange's OrderBook.

from order.base import Order
from old.agent.FinancialAgent import dollarize
from copy import deepcopy
import pandas as pd
from agent.base import Agent
from functools import total_ordering
from typing import Dict, List, TYPE_CHECKING
from heapdict import heapdict
from sortedcontainers import SortedList, SortedDict


import sys

# Module level variable that can be changed by config files.
silent_mode = False


@total_ordering
class LimitOrder(Order):

    def __init__(
        self,
        agent_id: int,
        time_placed: pd.Timestamp,
        symbol: str,
        quantity: int,
        is_buy_order: bool,
        limit_price: int,
        tag=None,
    ):

        super().__init__(agent_id, time_placed, symbol, quantity, is_buy_order, tag=tag)

        self.limit_price: int = limit_price
        self.compare_price: int = -limit_price if is_buy_order else limit_price

    def __eq__(self, other):
        if not isinstance(other, LimitOrder):
            return False
        return self.id == other.id

    def __lt__(self, other):
        # Compare LimitOrders based on their limit price
        if not isinstance(other, LimitOrder):
            return NotImplemented

        if self.compare_price == other.compare_price:
            return self.time_placed < other.time_placed
        return self.compare_price < other.compare_price


class OrderHeap:
    def __init__(self, side="ask"):
        self.side = -1.0 if side == "ask" else 1.0
        self.heap = heapdict()
        self.levels = SortedDict()

        # elements in self.levels are tuples of (price, volume)
        self.levels.key = lambda price_volume: price_volume[0] * self.side

    def put(self, order: LimitOrder):
        # 将 id 作为 key，order 作为 value，优先级由 order 本身定义
        self.heap[order.id] = order
        price = order.limit_price
        volume = order.quantity

    def get(self) -> LimitOrder:
        # 弹出最小优先级的 order
        _, order = self.heap.popitem()
        return order

    def get_by_id(self, order_id: int) -> LimitOrder:
        # 按 id 删除指定 order 并返回
        if order_id in self.heap:
            order = self.heap.pop(order_id)
            return order
        return None

    def peek(self) -> LimitOrder:
        # 返回当前最小优先级的 order（不删除）
        if self.heap:
            _, order = self.heap.peekitem()
            return order
        return None

    def empty(self):
        return len(self.heap) == 0

    def __len__(self):
        return len(self.heap)
