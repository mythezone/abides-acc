from core.agent.fundamental import FundamentalTrackingAgent
from core.message import MessageType, MessageQueue, Message, new_message

import numpy as np


class FCNAgent(FundamentalTrackingAgent):
    def __init__(
        self, id, *args, p_star, Z, mu, sigma, tau, T, k, initial_symbols=None, **kwargs
    ):
        super().__init__(id, *args, initial_symbols=initial_symbols, **kwargs)
        self.p_star = p_star
        self.Z = Z
        self.mu = mu
        self.sigma = sigma
        self.tau = tau
        self.T = T
        self.k = k

        self.selected_symbols = list(
            np.random.choice(
                initial_symbols, int(np.random.randint(1, 3)), replace=False
            )
        )
        self.time_step = 1
        self.prices = {}
        self.fundamental_prices = {}
        for symbol in self.selected_symbols:
            self.prices[symbol] = {}
            self.fundamental_prices[symbol] = {}

    def wakeup(self, currentTime):
        super().wakeup(currentTime)
        requests = []
        for symbol in self.selected_symbols:
            # 1. get the fundamental value and current price
            p_t_star = self.GBM(symbol=symbol)
            p_t = self.prices[symbol][str(self.time_step)]

            # 2. calculate return rate
            r = self.calc_return_rate(p=p_t, p_star=p_t_star, symbol=symbol)

            # 3. predict future price
            p_t_plus_tau = p_t * np.exp(r * self.tau)

            # 4. making trading decisions
            self.make_trading_decision(p=p_t, p_pred=p_t_plus_tau)

        self.send(requests)
        self.time_step += 1

    def GBM(self, symbol):
        """Return the result of fundamental price, which changes as a geometric Brownian motion, at the current timestamp."""
        t = self.time_step
        Z_t = self.Z(t)
        X_t = np.exp((self.mu - self.sigma**2 / 2) * t + self.sigma * Z_t)
        self.fundamental_prices.get(symbol).setdefault(key=str(t), default=X_t)
        return X_t

    def calc_return_rate(self, p, p_star, symbol):
        t = self.time_step
        T = self.T
        prev_p = self.prices[symbol][str(t - self.tau)]
        F = 1 / T * np.log(p_star / p)
        C = 1 / T * np.log(p / prev_p)
        N = np.random.normal(loc=0, scale=0.0001)
        rate_param = 0.5
        weights = np.random.exponential(scale=rate_param, size=3)
        return np.dot(weights, (F, C, N)) / np.sum(weights)

    def make_trading_decision(self, p, p_pred, requests: list, symbol: str):
        is_buy_order = True
        if p_pred > p:
            price = p_pred * (1 - self.k)
        else:
            price = p_pred * (1 + self.k)
            is_buy_order = False
        volume = np.random.randint(low=1, high=6)
        order = {
            "type": "limit_order",
            "symbol": symbol,
            "agent_id": self.id,
            "timestamp": str(self.current_time),
            "side": "buy" if is_buy_order else "sell",
            "quantity": volume,
            "price": price,
        }
        requests.append(order)
