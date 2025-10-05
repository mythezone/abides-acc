from core.agent.fundamental import FundamentalTrackingAgent
from core.message import MessageType, MessageQueue, Message, new_message
from typing import List, Optional

import numpy as np
import pandas as pd


class InformedAgent(FundamentalTrackingAgent):
    def __init__(
        self,
        id,
        durations,
        r,
        tau,
        alpha,
        sigma,
        *args,
        initial_symbols=None,
        **kwargs,
    ):
        super().__init__(id, *args, initial_symbols=initial_symbols, **kwargs)

        self.r = r  # return rate
        self.tau = tau  # look-back periods
        self.alpha = alpha  # alpha
        self.durations = durations  # T-d+1 in the formula
        self.sigma = sigma
        self.subscribed_symbols: List[str] = (initial_symbols or [])[:]
        self.selected_symbols = list(
            np.random.choice(
                initial_symbols, int(np.random.randint(1, 3)), replace=False
            )
        )

        self.time_step = 1
        self.common_values: dict[str, dict] = {}
        self.historical_prices: dict[str, dict] = {}
        for symbol in self.selected_symbols:
            self.common_values[symbol] = {}
            self.historical_prices[symbol] = {}

    def action(self):
        super().action()
        requests = []

        for symbol in self.selected_symbols:
            # 1. get p_hat
            p_hat = self._get_expected_price(
                t=self.time_step, tau=self.tau, symbol=symbol
            )

            # 2. get order submission price
            price = self._compute_submission_price(symbol=symbol, p_hat=p_hat)

            # 3. get desired position
            desired_position = self._compute_desired_position(
                symbol=symbol, submission_price=price
            )

            # 4. determine the order and add to the list
            self._determine_order(
                symbol=symbol,
                desired_position=desired_position,
                submission_price=price,
                requests=requests,
            )

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

        # always update local storage
        for symbol in self.selected_symbols:
            self._update_historical_prices(t=self.time_step, symbol=symbol)
            if self.time_step == 1:
                self._update_common_values(
                    t=self.time_step, symbol=symbol, period_to_update=100
                )

        # time step increment
        self.time_step += 1

    def process_inbox(self):
        super().process_inbox()
        for msg in self.inbox:
            pass

    def _get_expected_price(self, t, symbols: str):
        M_0 = self.get_M_0(t)
        S = []
        v = []
        for symbol in symbols:
            S.append(self.portfolio.holdings[symbol])
            v.append(self._get_common_values_safely(symbol, t))
        numerator = np.dot(S, v)
        denominator = M_0 * 3000 * (1 + self.r) ** self.durations
        return numerator / denominator

    def _compute_submission_price(self, symbol, p_hat):
        midpoint = np.mean(self.get_best_bid_ask(symbol))
        if midpoint is not None and p_hat is not None:
            # p_hat and midpoint may be floats/ints; compute average
            res = 0.5 * (float(p_hat) + float(midpoint))
        elif p_hat is not None:
            res = float(p_hat)
        elif midpoint is not None:
            res = float(midpoint)
        else:
            # no data -> don't submit aggressive price, return None to abort
            return None

        return int(round(res))

    def _compute_desired_position(self, symbol, p_hat, submission_price):
        if p_hat is None or submission_price is None:
            return None

        # variance estimate: use tau as lookback window (paper uses tau)
        V_it = self._estimate_variance(symbol, self.tau)

        # apply formula: pi = ln(p_hat / p) / (alpha * V * p)
        # if p_hat == p => ln = 0 => pi = 0 (no trade)
        try:
            numerator = np.log(max(p_hat, 1e-12) / max(submission_price, 1e-12))
        except ValueError:
            return None

        denominator = self.alpha * V_it * submission_price
        pi = numerator / denominator

        # desired position must be an integer number of shares/contracts
        # for stocks: round to nearest integer (we'll apply lot-size later)
        desired = int(round(pi))
        return desired

    def _estimate_variance(self, symbol, lookback, t):
        prices = self.historical_prices[symbol]
        returns = []

        for j in range(1, lookback + 1):
            t1 = str(t - j)
            t0 = str(t - j - 1)
            if t1 in prices and t0 in prices:
                p1 = float(prices[t1])
                p0 = float(prices[t0])
                if p0 > 0:
                    r = np.log(p1 / p0)
                    returns.append(r)
            else:
                break

        if len(returns) < 2:
            # insufficient data - return a conservative (large) variance to reduce position sizing
            return 1.0
        # sample variance
        return float(np.var(returns, ddof=1))

    def _determine_order(
        self, symbol, desired_position, submission_price, requests: list
    ):
        current = self.portfolio.holdings[symbol]
        delta = desired_position - current  # positive -> buy, negative -> sell
        if delta == 0:
            return
        qty = np.abs(delta)
        best_bid, best_ask = self.get_best_bid_ask(symbol)
        if delta > 0:
            if best_ask is not None and submission_price > best_ask:
                order = {
                    "type": "market_order",
                    "symbol": symbol,
                    "agent_id": self.id,
                    "timestamp": str(self.current_time),
                    "side": "buy",
                    "quantity": qty,
                }
            else:
                order = {
                    "type": "limit_order",
                    "symbol": symbol,
                    "agent_id": self.id,
                    "timestamp": str(self.current_time),
                    "side": "buy",
                    "quantity": qty,
                    "price": submission_price,
                }
        else:
            if best_bid is not None and submission_price <= best_bid:
                order = {
                    "type": "market_order",
                    "symbol": symbol,
                    "agent_id": self.id,
                    "timestamp": str(self.current_time),
                    "side": "sell",
                    "quantity": qty,
                }
            else:
                order = {
                    "type": "limit_order",
                    "symbol": symbol,
                    "agent_id": self.id,
                    "timestamp": str(self.current_time),
                    "side": "sell",
                    "quantity": qty,
                    "price": submission_price,
                }
        requests.append(order)

    def _update_common_values(self, symbol: str, t, period_to_update):
        """Update common values at the begging of t. The rest of the series is determined by a stochastic process."""
        msg = self.build_fundamental_query(symbols=[symbol])
        self.send(msg)
        msg_in: Message = self.message_queue.get_raw()
        if msg_in.message_type == MessageType.QUERY_FUNDAMENTAL:
            content = msg_in.content
            res = content["data"]

        # update local fundamental values storage
        self.common_values[symbol].setdefault(str(t), res)

        for period in range(period_to_update):
            value = self.common_values[symbol].get(str(period + 1)) * (
                1 + self.sigma * np.random.rand()
            )
        self.common_values[symbol].setdefault(str(period + 1), value)

    def _get_common_values_safely(self, symbol: str, t):
        if not self.common_values[symbol].get(str(t)):
            self._update_common_values(symbol=symbol, t=t, period_to_update=100)
        return self.common_values[symbol].get(str(t))

    def get_best_bid_ask(self, symbol: str):
        msg = self.build_top_of_book_query(symbols=[symbol])
        self.send(msg)
        msg_in: Message = self.message_queue.get_raw()
        if msg_in.message_type == MessageType.QUERY_TOP_OF_BOOK:
            content = msg_in.content
            return content["best bid"], content["best ask"]

    def _update_historical_prices(
        self,
        t,
        symbol: str,
        send_time: Optional[pd.Timestamp] = None,
    ):
        content = {"request": {"symbol": symbol}}
        time = send_time or self.current_time
        msg = new_message(
            message_type=MessageType.QUERY_LAST_TRADE,
            sender_id=self.id,
            recipient_id="Exchange",
            send_time=time,
            recive_time=time,
            content=content,
        )
        self.send(message=msg)
        msg_in: Message = self.message_queue.get_raw()
        if msg_in.message_type == MessageType.QUERY_LAST_TRADE:
            content = msg_in.content
            last_price = content["data"]

        # update local historical data storage
        self.historical_prices[symbol].setdefault(key=t, default=last_price)


class UninformedAgent(FundamentalTrackingAgent):
    def __init__(
        self,
        id,
        durations,
        r,
        tau,
        alpha,
        sigma,
        a,
        b,
        c,
        *args,
        initial_symbols=None,
        **kwargs,
    ):
        super().__init__(id, *args, initial_symbols=initial_symbols, **kwargs)

        self.r = r  # return rate
        self.tau = tau  # look-back periods
        self.alpha = alpha  # alpha
        self.durations = durations  # T-d+1 in the formula
        self.sigma = sigma
        self.a, self.b, self.c = a, b, c
        self.subscribed_symbols: List[str] = (initial_symbols or [])[:]
        self.selected_symbols = list(
            np.random.choice(
                initial_symbols, int(np.random.randint(1, 3)), replace=False
            )
        )

        self.time_step = 1
        self.common_values: dict[str, dict] = {}
        self.historical_prices: dict[str, dict] = {}
        for symbol in self.selected_symbols:
            self.common_values[symbol] = {}
            self.historical_prices[symbol] = {}

    def action(self):
        super().action()
        requests = []

        for symbol in self.selected_symbols:
            # 1. get p_hat
            p_hat = self._get_expected_price(t=self.time_step, symbol=symbol)

            # 2. get order submission price
            price = self._compute_submission_price(symbol=symbol, p_hat=p_hat)

            # 3. get desired position
            desired_position = self._compute_desired_position(
                symbol=symbol, submission_price=price
            )

            # 4. determine the order and add to the list
            self._determine_order(
                symbol=symbol,
                desired_position=desired_position,
                submission_price=price,
                requests=requests,
            )

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

        # always update local storage
        for symbol in self.selected_symbols:
            self._update_historical_prices(t=self.time_step, symbol=symbol)
            if self.time_step == 1:
                self._update_common_values(
                    t=self.time_step, symbol=symbol, period_to_update=100
                )

        # time step increment
        self.time_step += 1

    def process_inbox(self):
        super().process_inbox()
        for msg in self.inbox:
            pass

    def _get_expected_price(self, t, symbol: str):
        v_t = self.historical_prices[str(t)]
        p_tau_bar = 0
        for i in range(self.tau):
            p_tau_bar += self.historical_prices[str(t - i)]
        p_tau_bar /= self.tau
        midpoint = np.mean(self.get_best_bid_ask(symbol))

        return np.dot((self.a, self.b, self.c), (v_t, p_tau_bar, midpoint)) / np.sum(
            self.a, self.b, self.c
        )

    def _compute_submission_price(self, symbol, p_hat):
        midpoint = np.mean(self.get_best_bid_ask(symbol))
        if midpoint is not None and p_hat is not None:
            # p_hat and midpoint may be floats/ints; compute average
            res = 0.5 * (float(p_hat) + float(midpoint))
        elif p_hat is not None:
            res = float(p_hat)
        elif midpoint is not None:
            res = float(midpoint)
        else:
            # no data -> don't submit aggressive price, return None to abort
            return None

        return int(round(res))

    def _compute_desired_position(self, symbol, p_hat, submission_price):
        if p_hat is None or submission_price is None:
            return None

        # variance estimate: use tau as lookback window (paper uses tau)
        V_it = self._estimate_variance(symbol, self.tau)

        # apply formula: pi = ln(p_hat / p) / (alpha * V * p)
        # if p_hat == p => ln = 0 => pi = 0 (no trade)
        try:
            numerator = np.log(max(p_hat, 1e-12) / max(submission_price, 1e-12))
        except ValueError:
            return None

        denominator = self.alpha * V_it * submission_price
        pi = numerator / denominator

        # desired position must be an integer number of shares/contracts
        # for stocks: round to nearest integer (we'll apply lot-size later)
        desired = int(round(pi))
        return desired

    def _estimate_variance(self, symbol, lookback, t):
        prices = self.historical_prices[symbol]
        returns = []

        for j in range(1, lookback + 1):
            t1 = str(t - j)
            t0 = str(t - j - 1)
            if t1 in prices and t0 in prices:
                p1 = float(prices[t1])
                p0 = float(prices[t0])
                if p0 > 0:
                    r = np.log(p1 / p0)
                    returns.append(r)
            else:
                break

        if len(returns) < 2:
            # insufficient data - return a conservative (large) variance to reduce position sizing
            return 1.0
        # sample variance
        return float(np.var(returns, ddof=1))

    def _determine_order(
        self, symbol, desired_position, submission_price, requests: list
    ):
        current = self.portfolio.holdings[symbol]
        delta = desired_position - current  # positive -> buy, negative -> sell
        if delta == 0:
            return
        qty = np.abs(delta)
        best_bid, best_ask = self.get_best_bid_ask(symbol)
        if delta > 0:
            if best_ask is not None and submission_price > best_ask:
                order = {
                    "type": "market_order",
                    "symbol": symbol,
                    "agent_id": self.id,
                    "timestamp": str(self.current_time),
                    "side": "buy",
                    "quantity": qty,
                }
            else:
                order = {
                    "type": "limit_order",
                    "symbol": symbol,
                    "agent_id": self.id,
                    "timestamp": str(self.current_time),
                    "side": "buy",
                    "quantity": qty,
                    "price": submission_price,
                }
        else:
            if best_bid is not None and submission_price <= best_bid:
                order = {
                    "type": "market_order",
                    "symbol": symbol,
                    "agent_id": self.id,
                    "timestamp": str(self.current_time),
                    "side": "sell",
                    "quantity": qty,
                }
            else:
                order = {
                    "type": "limit_order",
                    "symbol": symbol,
                    "agent_id": self.id,
                    "timestamp": str(self.current_time),
                    "side": "sell",
                    "quantity": qty,
                    "price": submission_price,
                }
        requests.append(order)

    def _update_common_values(self, symbol: str, t, period_to_update):
        """Update common values begging at t. The rest of the series is determined by a stochastic process."""
        msg = self.build_fundamental_query(symbols=[symbol])
        self.send(msg)
        msg_in: Message = self.message_queue.get_raw()
        if msg_in.message_type == MessageType.QUERY_FUNDAMENTAL:
            content = msg_in.content
            res = content["data"]

        # update local fundamental values storage
        self.common_values[symbol].setdefault(str(t), res)

        for period in range(period_to_update):
            value = self.common_values[symbol].get(str(period + 1)) * (
                1 + self.sigma * np.random.rand()
            )
        self.common_values[symbol].setdefault(str(period + 1), value)

    def _get_common_values_safely(self, symbol: str, t):
        if not self.common_values[symbol].get(str(t)):
            self._update_common_values(symbol=symbol, t=t, period_to_update=100)
        return self.common_values[symbol].get(str(t))

    def get_best_bid_ask(self, symbol: str):
        msg = self.build_top_of_book_query(symbols=[symbol])
        self.send(msg)
        msg_in: Message = self.message_queue.get_raw()
        if msg_in.message_type == MessageType.QUERY_TOP_OF_BOOK:
            content = msg_in.content
            return content["best bid"], content["best ask"]

    def _update_historical_prices(
        self,
        t,
        symbol: str,
        send_time: Optional[pd.Timestamp] = None,
    ):
        content = {"request": {"symbol": symbol}}
        time = send_time or self.current_time
        msg = new_message(
            message_type=MessageType.QUERY_LAST_TRADE,
            sender_id=self.id,
            recipient_id="Exchange",
            send_time=time,
            recive_time=time,
            content=content,
        )
        self.send(message=msg)
        msg_in: Message = self.message_queue.get_raw()
        if msg_in.message_type == MessageType.QUERY_LAST_TRADE:
            content = msg_in.content
            last_price = content["data"]

        # update local historical data storage
        self.historical_prices[symbol].setdefault(key=t, default=last_price)
