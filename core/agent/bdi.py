from core.agent.fundamental import FundamentalTrackingAgent
from core.message import MessageType, MessageQueue, Message, new_message
from collections import deque

import numpy as np


class BDIAgent(FundamentalTrackingAgent):
    def __init__(
        self, id, *args, genome, starting_cash, initial_stocks=None, **kwargs
    ):
        super().__init__(id, *args, initial_stocks=initial_stocks, **kwargs)

        self.genome = genome
        self.starting_cash = starting_cash

        self.beliefs = {}
        self.desires = {}
        self.goals = {}

        # technical trust degree: alpha_1 ~ alpha_22
        self.trust_alpha = genome[1:23]

        # trading behaviour parameters
        # gb1 ~ gb5
        self.buy_params = genome[23:28]
        # ga1 ~ ga5
        self.sell_params = genome[28:]

        self.last_price = None
        self.price_concession = {}

        self.price_history = {}
        self.selected_smbols = list(
            np.random.choice(
                initial_stocks, int(np.random.randint(1, 3)), replace=False
            )
        )
        for stock in self.selected_smbols:
            self.price_history[stock] = []
            self.price_concession[stock] = {"buy": 0, "sell": 0}
            self.last_price[stock] = None

    def action(self):
        super().action()

        requests = []
        for sym in self.selected_smbols:
            # 1. update beliefs
            self.update_beliefs(stock=sym)
            # 2. generate desires
            self.generate_desires(stock=sym)
            # 3. form goals
            self.form_goals()
            # 4. excute buy or sell actions
            self.execute_actions(requests)
            # submit the orders
        if requests:
            msg = new_message(
                message_type=MessageType.SUBMIT_ORDER,
                sender_id=self.id,
                recipient_id="Exchange",
                send_time=self.current_time,
                recive_time=self.current_time,
                content={"requests": requests},
            )
            self.send(msg)

    def update_beliefs(self, stock):
        tech_indicators = self.get_technical_indicators()
        belief_up = 0.0

        for i, indicator in enumerate(tech_indicators):
            alpha = self.trust_alpha[i]
            if indicator > 0:
                belief_up = belief_up * (1 - alpha) + alpha
            elif indicator < 0:
                belief_up = belief_up * (1 - alpha)

        self.beliefs["u"] = np.clip(belief_up, 0, 1)
        self.beliefs["-u"] = 1 - self.beliefs["u"]

        self.beliefs["cash"] = (
            1.0 if self.portfolio.cash > self.starting_cash * 0.1 else 0.0
        )
        self.beliefs["asset"] = 1.0 if self.portfolio.holdings[stock] > 10 else 0.0

    def get_technical_indicators(self, stock) -> list:
        """Return all technical indicators as a list."""
        # make sure that there are enough historical data
        if stock not in self.price_history.keys():
            self.price_history[stock] = deque(maxlen=50)

        # get current price
        current_price = self.last_price.get(stock)
        if current_price is None:
            return [0] * 22

        # update historical price
        self.price_history[stock].append(current_price)
        prices = list(self.price_history[stock])
        n = len(prices)

        indicators = np.zeros(22)

        # 1 ~ 5
        for i in range(5):
            depth = i + 2
            if n >= depth:
                index = -1 - i
                if index < -n:
                    continue
                indicators[i] = 1 if prices[index] > prices[index - 1] else 0

        # 6 ~ 11
        sma_5 = np.log(current_price / self.calc_sma(prices=prices, window=5)) * (
            n >= 6
        )
        sma_10 = np.log(current_price / self.calc_sma(prices=prices, window=10)) * (
            n >= 11
        )
        sma_20 = np.log(current_price / self.calc_sma(prices=prices, window=20)) * (
            n >= 21
        )
        ema_5 = np.log(current_price / self.calc_ema(prices=prices, window=5)) * (
            n >= 6
        )
        ema_10 = np.log(current_price / self.calc_ema(prices=prices, window=10)) * (
            n >= 11
        )
        ema_20 = np.log(current_price / self.calc_ema(prices=prices, window=20)) * (
            n >= 21
        )

        indicators[5] = 1 if current_price > sma_5 else 0

        indicators[6] = 1 if current_price > sma_10 else 0

        indicators[7] = 1 if current_price > sma_20 else 0

        indicators[8] = 1 if current_price > ema_5 else 0

        indicators[9] = 1 if current_price > ema_10 else 0

        indicators[10] = 1 if current_price > ema_20 else 0

        # 12 ~ 15
        sma_50 = np.log(current_price / self.calc_sma(prices=prices, window=50)) * (
            n >= 51
        )
        ema_50 = np.log(current_price / self.calc_ema(prices=prices, window=50)) * (
            n >= 51
        )

        indicators[11] = 1 if current_price / sma_5 > sma_20 else 0
        indicators[12] = 1 if current_price / sma_5 > sma_50 else 0
        indicators[13] = 1 if current_price / ema_5 > ema_20 else 0
        indicators[14] = 1 if current_price / ema_5 > ema_50 else 0

    def generate_desires(self, stock):
        self.desires["buy"] = self.beliefs["u"]
        self.desires["sell"] = self.beliefs["-u"]

        cash_threshold = self.portfolio.cash > self.starting_cash * 0.1
        asset_threshold = self.portfolio.holdings[stock] > 10

        # The values are kept if True or be set to 0 if False.
        self.desires["buy"] *= cash_threshold
        self.desires["sell"] *= asset_threshold

        if "buy" in self.desires and self.beliefs["cash"] > 0.5:
            self.desires["buy"] *= self.beliefs["cash"]
        else:
            self.desires.pop("buy", None)

        if "sell" in self.desires and self.beliefs["asset"] > 0.5:
            self.desires["sell"] *= self.beliefs["asset"]
        else:
            self.desires.pop("sell", None)

    def form_goals(self):
        buy_desire = self.desires.get("buy", 0)
        sell_desire = self.desires.get("sell", 0)

        if buy_desire > sell_desire and buy_desire > 0.5:
            self.goals = {"buy": buy_desire}
        elif sell_desire > buy_desire and sell_desire > 0.5:
            self.goals = {"sell": sell_desire}
        else:
            self.goals = {}

    def execute_actions(self, stock, requests: list):
        if "buy" in self.goals:
            self.place_buy_order(stock=stock, requests=requests)
        elif "sell" in self.goals:
            self.place_sell_order(stock=stock, requests=requests)

    def place_buy_order(self, stock, requests: list):
        goal_strenth = self.goals["buy"]
        gb1, gb2, gb3, gb4, gb5 = self.buy_params

        M = self.portfolio.cash
        A = self.portfolio.holdings[stock]

        # calculate total value of the bid
        if A < gb2:
            V_bid = M * (gb1 + (1 - gb1) * gb3 * goal_strenth)
        else:
            V_bid = M * gb1

        # update price concession
        if self.price_concession[stock]["buy"] == 0:
            self.price_concession[stock]["buy"] = 2 * goal_strenth + gb4
        else:
            c = self.price_concession[stock]["buy"]
            self.price_concession[stock]["buy"] = c + (1 - c) * (
                4 * goal_strenth + gb5
            )

        p_bid = self.last_price.get(stock) * (1 - self.price_concession[stock]["buy"])
        q_bid = V_bid / p_bid

        if q_bid > 0:
            # place a buy limit order at price p_bid and quantity q_bid for stock
            order = {
                "type": "limit_order",
                "stock": stock,
                "agent_id": self.id,
                "timestamp": str(self.current_time),
                "side": "buy",
                "quantity": q_bid,
                "price": p_bid,
            }
            requests.append(order)

    def place_sell_order(self, stock, requests: list):
        goal_strenth = self.goals["sell"]
        ga1, ga2, ga3, ga4, ga5 = self.buy_params

        M = self.portfolio.cash
        A = self.portfolio.holdings[stock]

        # calculate total value of the bid
        if A < ga2:
            V_ask = A * (ga1 + (1 - ga1) * ga3 * goal_strenth)
        else:
            V_ask = A * ga1

        # update price concession
        if self.price_concession[stock]["sell"] == 0:
            self.price_concession[stock]["sell"] = 2 * goal_strenth + ga4
        else:
            c = self.price_concession[stock]["sell"]
            self.price_concession[stock]["sell"] = c + (1 - c) * (
                4 * goal_strenth + ga5
            )

        p_ask = self.last_price.get(stock) * self.price_concession[stock]["sell"]
        q_ask = V_ask / p_ask

        if q_ask > 0:
            # place a sell limit order at price p_bid and quantity q_bid for stock
            order = {
                "type": "limit_order",
                "stock": stock,
                "agent_id": self.id,
                "timestamp": str(self.current_time),
                "side": "sell",
                "quantity": q_ask,
                "price": p_ask,
            }
            requests.append(order)

    def process_inbox(self):
        super().process_inbox()
        remaining = []
        for msg in self.inbox:
            msg: Message
            if msg.message_type == MessageType.ORDER_EXECUTED and isinstance(
                msg.content, dict
            ):
                stock = msg.content.get("stock")
                if msg.content.get("side") == "buy":
                    self.price_concession[stock]["buy"] = 0
                elif msg.content.get("side") == "sell":
                    self.price_concession[stock]["sell"] = 0
            elif msg.message_type == MessageType.MKT_CLOSE and isinstance(
                msg.content, dict
            ):
                self.price_concession[stock] = {"buy": 0, "sell": 0}
            elif msg.message_type == MessageType.QUERY_LAST_TRADE and isinstance(
                msg.content, dict
            ):
                content = msg.content
                stock = content["stock"]
                last_price = content["data"]
                self.last_price[stock] = last_price
                self.update_price_history(self.last_price, stock)
            else:
                remaining.append(msg)
        self.inbox = remaining

    def update_price_history(self, price, stock):
        if stock not in self.price_history.keys():
            self.price_history[stock] = deque(maxlen=50)
        self.price_history[stock].append(price)
