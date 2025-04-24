import random
from core.message import Message
from agent.base import Agent

import pandas as pd
import numpy as np


import unittest

random_state = np.random.RandomState(42)


class TestMessage(unittest.TestCase):

    def test_agent_init(self):
        # Test initialization with valid parameters
        for i in range(5):
            Agent(
                name="TestAgent",
                type="TestType",
                random_state=random_state,
                log_to_file=False,
            )
        self.assertEqual(len(Agent.agents_list), 5)
        agent = Agent.get_agent_by_id(0)
        self.assertIsInstance(agent, Agent)
        self.assertEqual(agent.name, "TestAgent")

    def test_message_init(self):
        # Test initialization with valid parameters
        self.assertEqual(len(Agent.agents_list), 5)

        for i in range(5):
            Message(
                message_type=34,
                sender=1,
                recipient=2,
                send_time=pd.Timestamp("2023-10-01"),
                content={"key": "value"},
            )
        self.assertEqual(len(Message.message_list), 5)
        message = Message.get_message_by_id(0)
        self.assertIsInstance(message, Message)
        self.assertEqual(message.sender, Agent.get_agent_by_id(1))
        self.assertEqual(message.recipient, Agent.get_agent_by_id(2))
        self.assertEqual(message.send_time, pd.Timestamp("2023-10-01"))
        self.assertEqual(message.content, {"key": "value"})


if __name__ == "__main__":
    unittest.main()
