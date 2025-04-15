from order.limit_order import LimitOrder
import unittest
from agent.base import Agent
from numpy import random
from pandas import Timestamp
from order.limit_order import OrderHeap


class TestOrder(unittest.TestCase):
    def setUp(self):
        # Clear any existing subclass instances
        LimitOrder._subclass_instances.clear()
        Agent._subclass_instances.clear()

        # Initialize agents and orders
        self.agents = []
        self.orders = []
        for i in range(10):
            self.agents.append(
                Agent(type_="Trader", random_state=random.RandomState(42))
            )

        for i in range(10):
            self.orders.append(
                LimitOrder(
                    agent_id=Agent[i].id,
                    time_placed=Timestamp.now(),
                    symbol="AAPL",
                    quantity=random.randint(1, 100),
                    limit_price=random.randint(100, 200),
                    is_buy_order=True,
                    tag={"test": "tag"},
                )
            )
        self.book = OrderHeap()

    def test_to_dict(self):
        for i in range(10):
            self.assertEqual(self.orders[i], LimitOrder[i])
            self.assertEqual(self.agents[i], Agent[i])
