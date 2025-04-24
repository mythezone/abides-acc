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
        self.assertIs(self.symbol1, Symbol["AAPL"])

    def test_symbol_len(self):
        self.assertEqual(Symbol.size(), 3)
        Symbol("TSLA", 0.01)
        self.assertEqual(Symbol.size(), 4)

    def test_symbol_iter(self):
        # for v in Symbol:
        #     self.assertIn(v, [self.symbol1, self.symbol2, self.symbol3])
        self.assertEqual(self.symbol1.name, "AAPL")
        self.assertEqual(self.symbol1.r_bar, 0.02)
        # for v in Symbol:
        #     self.assertIn(v, [self.symbol1, self.symbol2, self.symbol3])
        for v in Symbol:
            self.assertIn(v, [self.symbol1, self.symbol2, self.symbol3])

    def test_random_symbol(self):
        random_symbol = Symbol.get_random_symbol()
        self.assertIn(random_symbol, [self.symbol1, self.symbol2, self.symbol3])
