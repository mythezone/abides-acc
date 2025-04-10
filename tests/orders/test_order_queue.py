from order.base import Order
from order.order_book import OrderBook
from order.limit_order import LimitOrder
import unittest
import pandas as pd

# from util.util import OrderHeap


class TestOrderBook(unittest.TestCase):
    def setUp(self):
        Order._subclass_instances.clear()
        self.order1 = LimitOrder(
            agent_id=1,
            time_placed=pd.Timestamp.now(),
            symbol="AAPL",
            quantity=10,
            limit_price=150,
            is_buy_order=True,
        )
        self.order2 = LimitOrder(
            agent_id=2,
            time_placed=pd.Timestamp.now(),
            symbol="AAPL",
            quantity=5,
            limit_price=155,
            is_buy_order=True,
        )
        LimitOrder(
            agent_id=3,
            time_placed=pd.Timestamp.now(),
            symbol="AAPL",
            quantity=5,
            limit_price=144,
            is_buy_order=False,
        )
        LimitOrder(
            agent_id=4,
            time_placed=pd.Timestamp.now(),
            symbol="AAPL",
            quantity=5,
            limit_price=135,
            is_buy_order=False,
        )
        self.order_book = OrderBook("AAPL")
        self.order_book2 = OrderBook("GOOGL")

    def test_add_order(self):
        self.order_book.ask_side.put(self.order1)
        self.order_book.ask_side.put(self.order2)
        self.order_book.ask_side.put(LimitOrder[2])
        self.order_book.ask_side.put(LimitOrder[3])

        self.assertEqual(self.order_book.ask_side.get(), self.order2)
