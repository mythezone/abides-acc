from order.base import Order 
import unittest
from agent.base import Agent
from numpy import random 
from pandas import Timestamp


class TestOrder(unittest.TestCase):
    def setUp(self):
        self.agents = []
        self.orders = []
        for i in range(10):
            self.agents.append(Agent(name="Agent1",type="Trader",random_state=random.RandomState(42)))

        for i in range(10):
            self.orders.append(Order(agent=Agent[i], time_placed=Timestamp.now(), symbol="AAPL", quantity=i, is_buy_order=True, tag={"test": "tag"}))
    
    def test_to_dict(self):
        for i in range(10):
            self.assertEqual(self.orders[i], Order[i])
            self.assertEqual(self.agents[i], Agent[i])