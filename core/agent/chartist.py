from core.agent.fundamental import FundamentalTrackingAgent
from core.message import MessageType, MessageQueue, Message, new_message
from collections import deque

import numpy as np


class Chartist(FundamentalTrackingAgent):
    def __init__(self, id, D, beta, delta_c, *args, initial_stocks=None, **kwargs):
        super().__init__(id, *args, initial_stocks=initial_stocks, **kwargs)

        self.D = D  # period of moving average
        self.beta = beta
        self.delta_c = delta_c

        # historical prices
        self.historical_prices = {}
        # time-step, 1-indexed
        self.time_step = 1
        self.selected_stocks = list(
            np.random.choice(
                initial_stocks, int(np.random.randint(1, 3)), replace=False
            )
        )

    def action(self):
        super().action()

        # do nothing until queryLastTrade is invoked at least once
        if self.time_step == 1:
            return

        requests = []
        for stock in self.selected_stocks:
            # 1. get the latest price
            p = self.historical_prices[str(self.time_step)]

            # 2. get the moving average price
            m = self.get_moving_average_price()

            # 3. making trading decision
            self.make_trading_decision(
                price=p, moving_avg_price=m, stock=stock, requests=requests
            )

    def get_moving_average_price(self):
        if len(self.historical_prices) <= self.D:
            return np.average(self.historical_prices.values())

        sum_of_prev_prices = 0
        for i in range(self.D):
            key = i - 2
            sum_of_prev_prices += self.historical_prices[str(key)]
        return sum_of_prev_prices / self.D

    def make_trading_decision(self, price, moving_avg_price, stock, requests):
        H = np.sign(price - moving_avg_price)
        qty = np.floor(self.beta * np.abs(price - moving_avg_price))
        if H > 0:
            z = np.random.normal(loc=0, scale=1)
            limit_price = price * (1 + np.abs(self.delta_c * z))
            # place a buy limit order at price limit_price, quantity q
            order = {
                "type": "limit_order",
                "stock": stock,
                "agent_id": self.id,
                "timestamp": str(self.current_time),
                "side": "buy",
                "quantity": qty,
                "price": limit_price,
            }
            requests.append(order)
        else:
            z = np.random.normal(loc=0, scale=1)
            limit_price = price * (1 - np.abs(self.delta_c * z))
            # place a sell limit order at price limit_price, quantity q
            order = {
                "type": "market_order",
                "stock": stock,
                "agent_id": self.id,
                "timestamp": str(self.current_time),
                "side": "buy",
                "quantity": qty,
                "price": limit_price,
            }

    def process_inbox(self):
        super().process_inbox()
        remaining = []
        for msg in self.inbox:
            msg: Message
            if msg.message_type == MessageType.QUERY_LAST_TRADE and isinstance(
                msg.content, dict
            ):
                content = msg.content
                stock = content["stock"]
                last_price = content["data"]
                self.last_price = last_price
                self.update_price_history(self.last_price, stock)
            else:
                remaining.append(msg)
        self.inbox = remaining

    def update_price_history(self, price, stock):
        if stock not in self.historical_prices:
            self.historical_prices[stock] = deque(maxlen=50)
        self.historical_prices[stock].append(price)
