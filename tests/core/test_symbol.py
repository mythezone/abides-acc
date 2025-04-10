import unittest 
from core.symbol import Symbol


class TestSymbol(unittest.TestCase):
    def setUp(self):
        Symbol._symbol_dict.clear()

        self.symbol1 = Symbol("AAPL", 0.02)
        self.symbol2 = Symbol("GOOGL", 0.03)
        self.symbol3 = Symbol("MS", 0.04)

    def test_symbol_creation(self):
        self.assertEqual(self.symbol1.name, "AAPL")
        self.assertEqual(self.symbol1.r_bar, 0.02)
        self.assertEqual(self.symbol2.name, "GOOGL")
        self.assertEqual(self.symbol2.r_bar, 0.03)
        self.assertEqual(self.symbol3.name, "MS")
        self.assertEqual(self.symbol3.r_bar, 0.04)

    def test_symbol_singleton(self):
        self.assertIs(self.symbol1, Symbol.get_symbol_by_name("AAPL"))
        self.assertIsNot(self.symbol1, self.symbol3)
        self.assertIs(self.symbol2, Symbol.get_symbol_by_name("GOOGL"))
        self.assertIs(self.symbol3, Symbol.get_symbol_by_name("MS"))
        self.assertIs(self.symbol1,Symbol["AAPL"])




