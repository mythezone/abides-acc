import numpy as np
from typing import List, Dict, Optional


class Portfolio:
    def __init__(self, initial_cash: float = 0.0):
        self.holdings: Dict[str, int] = {}  # symbol -> shares
        self.cash: float = float(initial_cash)
        self.initial_value: float = float(initial_cash)
        self.daily_values: Dict[str, float] = {}  # date -> total_value
        self.daily_logs: List[str] = []
        self.last_price: Dict[str, float] = {}  # symbol -> last known price for MTM

    def initialize_random_portfolio(
        self,
        symbols: List[str],
        min_shares: int = 0,
        max_shares: int = 1000,
        min_cash: float = 10000.0,
        max_cash: float = 1000000.0,
    ):
        self.cash = round(float(np.random.uniform(min_cash, max_cash)), 2)
        for symbol in symbols:
            shares = int(np.random.randint(min_shares, max_shares + 1))
            self.holdings[symbol] = shares
        self.initial_value = self.cash

    def current_total_value(self, current_prices: Optional[Dict[str, float]] = None) -> float:
        total = float(self.cash)
        if current_prices is None:
            # Use last known prices
            for symbol, shares in self.holdings.items():
                total += shares * float(self.last_price.get(symbol, 0.0))
        else:
            for symbol, shares in self.holdings.items():
                total += shares * float(current_prices.get(symbol, 0.0))
        return float(total)

    def apply_trade(self, symbol: str, side: str, price: float, quantity: int):
        # Update holdings and cash at execution time
        price = float(round(price, 2))
        qty = int(quantity)
        if side == "buy":
            self.cash -= price * qty
            self.holdings[symbol] = int(self.holdings.get(symbol, 0) + qty)
        elif side == "sell":
            self.cash += price * qty
            self.holdings[symbol] = int(self.holdings.get(symbol, 0) - qty)
            if self.holdings[symbol] <= 0:
                # Remove empty positions for cleanliness
                self.holdings.pop(symbol, None)
        self.last_price[symbol] = price

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
