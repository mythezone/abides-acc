# A basic Order type used by an Exchange to conduct trades or maintain an order book.
# This should not be confused with order Messages agents send to request an Order.
# Specific order types will inherit from this (like LimitOrder).

from copy import deepcopy
from agent.base import Agent

import pandas as pd
import numpy as np
from typing import Dict, List

from core.base import Trackable


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

        self.transaction = []

    def to_dict(self):
        as_dict = deepcopy(self).__dict__
        as_dict["time_placed"] = self.time_placed.isoformat()
        return as_dict
