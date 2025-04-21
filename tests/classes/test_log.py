# Create a new file named `test_logger.py` in the same directory as `logger.py`.
# In `test_logger.py`, add the following unit test code:

import os
import pandas as pd
from util.logger import Logger

import unittest

class TestLogger(unittest.TestCase):
    def setUp(self):
        self.logger1 = Logger(log_file='test_logs/simulation.log')
        self.logger2 = Logger(log_file='test_logs/simulation.log')
# Clean up the log file after tests

    def test_log_single_message(self):
        self.logger1.log("Test message")
        self.assertIn("Test message", self.logger1.messages[0])

    def test_log_multiple_messages(self):
        for i in range(5):
            self.logger1.log(f"Test message {i}")
            self.logger2.log(f"Test message {i}")
        self.assertEqual(len(self.logger1.messages), 10)

        self.logger1.dump()
        self.assertTrue(os.path.exists(self.logger2.log_file))