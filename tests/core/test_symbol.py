import unittest
from core.symbol import Symbol


class TestSymbol(unittest.TestCase):
    def setUp(self):
        self.symbol1 = Symbol("000001")

    def test_symbol_creation(self):
        self.assertEqual(self.symbol1.code, "000001")
        self.assertIsNotNone(self.symbol1.real_history)
        self.assertTrue(len(self.symbol1.real_history) > 0)
