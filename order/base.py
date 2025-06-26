# A basic Order type used by an Exchange to conduct trades or maintain an order book.
# This should not be confused with order Messages agents send to request an Order.
# Specific order types will inherit from this (like LimitOrder).

from copy import deepcopy
import enum
from agent.base import Agent

import pandas as pd
import numpy as np
import heapq
from dataclasses import dataclass

from typing import Dict, List, TYPE_CHECKING

from core.base import Trackable


# 类型包括： partial_deal | canceled | modified | finished
class OrderType(enum.Enum):
    """
    Enum for different types of orders.
    """

    TRADE = "trade"  # 普通交易
    PARTIAL_DEAL = "partial_deal"
    CANCELED = "canceled"
    MODIFIED = "modified"
    FINISHED = "finished"


@dataclass
class Transaction:
    id: int  # 交易ID
    time: pd.Timestamp

    symbol: str  # 股票代码
    price: int  # 价格单位为分
    quantity: int  # 数量单位为股

    bid_order_id: int = None  # 买单ID
    ask_order_id: int = None  # 卖单ID

    bid_agent_id: int = None  # 买方代理ID
    ask_agent_id: int = None  # 卖方代理ID
    trade: OrderType = OrderType.TRADE  # 交易类型，默认为 trade


class Order(Trackable):
    _order_id = 0
    _all_orders = []

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

        self.order_id = Order._order_id
        Order._order_id += 1
        Order._all_orders.append(self)

        self.agent_id = agent_id
        self.time_placed = time_placed
        self.symbol = symbol
        self.quantity = quantity
        self.is_buy_order = is_buy_order
        self.tag = tag

        self.remaining_quantity = quantity
        self.fill_price = None

        self.histories: List = []

    def to_dict(self):
        as_dict = deepcopy(self).__dict__
        as_dict["time_placed"] = self.time_placed.isoformat()
        return as_dict

    def deal(self, transaction: Transaction):
        self.histories.append(transaction)
        self.remaining_quantity -= transaction.quantity
        self.fill_price = transaction.price
        if self.remaining_quantity == 0:
            self.finish()

    def cancel(self, transaction: Transaction):
        self.histories.append(transaction)
        self.remaining_quantity = 0
        self.fill_price = transaction.price

    def modify(self, transaction: Transaction):
        self.histories.append(transaction)
        self.remaining_quantity = transaction.quantity
        self.fill_price = transaction.price

    # 结算
    def finish(self):
        pass  # TODO

    @classmethod
    def get_instance_by_id(cls, id_):
        if id_ < len(cls._all_orders):
            return cls._all_orders[id_]
        else:
            raise ValueError(f"Order ID {id_} not found.")

    @classmethod
    def __class_getitem__(cls, id_):
        return cls.get_instance_by_id(id_)

    @staticmethod
    def size():
        return len(Order._all_orders)
