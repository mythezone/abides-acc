# A basic Order type used by an Exchange to conduct trades or maintain an order book.
# This should not be confused with order Messages agents send to request an Order.
# Specific order types will inherit from this (like LimitOrder).

from copy import deepcopy
from agent.base import Agent

import pandas as pd
import numpy as np
from typing import Dict, List, TYPE_CHECKING

if TYPE_CHECKING:
    from order.base import Order

from core.base import Trackable


class Transaction:
    def __init__(self, time: pd.Timestamp, price: int, quantity: int, order: Order):
        self.time = time
        self.price = price
        self.quantity = quantity
        self.order = order


class Order(Trackable):
    def __init__(
        self,
        agent_id: int,
        time_placed: pd.Timestamp,
        symbol: str,
        quantity: int,
        is_buy_order: bool,
        tag: Dict = {},
    ):
        super().__init__()

        self.agent_id = agent_id
        self.time_placed = time_placed
        self.symbol = symbol
        self.quantity = quantity
        self.is_buy_order = is_buy_order
        self.tag = tag

        self.remaining_quantity = quantity
        self.fill_price = None

        self.transaction: List[Transaction] = []

    def to_dict(self):
        as_dict = deepcopy(self).__dict__
        as_dict["time_placed"] = self.time_placed.isoformat()
        return as_dict
