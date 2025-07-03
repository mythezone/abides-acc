import numpy as np
from core.symbol import Symbol
from typing import List, Dict


class Portfolio:
    def __init__(self):
        self.holdings = {}  # symbol -> shares
        self.cash = 0.0
        self.initial_value = 0.0
        self.daily_values = {}  # date -> total_value
        self.daily_logs = []

    def initialize_random_portfolio(
        self,
        symbols: List[Symbol],
        prev_date: str,
        min_shares: int = 0,
        max_shares: int = 1000,
        min_cash: float = 10000.0,
        max_cash: float = 1000000.0,
    ):
        self.cash = round(np.random.uniform(min_cash, max_cash), 2)
        total_value = self.cash
        for symbol_obj in symbols:
            symbol = symbol_obj.code
            ohlc = symbol_obj.get_real_ohlc(prev_date)
            prev_close = ohlc["收盘"] if ohlc["收盘"] is not None else 0
            shares = np.random.randint(min_shares, max_shares + 1)
            self.holdings[symbol] = shares
            total_value += shares * prev_close
        self.initial_value = total_value

    def current_total_value(self, current_prices):
        total = self.cash
        for symbol, shares in self.holdings.items():
            total += shares * current_prices.get(symbol, 0.0)
        return total

    def snapshot(self, date, current_prices: Dict):
        snapshot_text = f"Date: {date}\n"
        snapshot_text += f"Cash: {self.cash:.2f}\n"
        snapshot_text += "Holdings:\n"
        for symbol, shares in self.holdings.items():
            price = current_prices.get(symbol, 0.0)
            snapshot_text += f"  {symbol}: {shares} shares @ {price:.2f}\n"
        snapshot_text += (
            f"Total Value: {self.current_total_value(current_prices):.2f}\n"
        )
        return snapshot_text

    def record_daily_value(self, date, current_prices):
        value = self.current_total_value(current_prices)
        self.daily_values[date] = value
        log_text = self.snapshot(date, current_prices)
        self.daily_logs.append(log_text)

    def average_daily_return(self):
        values = list(self.daily_values.values())
        if len(values) < 2:
            return 0.0
        returns = [
            (values[i] - values[i - 1]) / values[i - 1]
            for i in range(1, len(values))
            if values[i - 1] != 0
        ]
        return np.mean(returns)
