# LimitOrder class, inherits from Order class, adds a limit price.  These are the
# Orders that typically go in an Exchange's OrderBook.

from order.base import Order
from core.kernel import Kernel
from agent.FinancialAgent import dollarize
from copy import deepcopy
import pandas as pd
from agent.base import Agent
from functools import total_ordering

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
