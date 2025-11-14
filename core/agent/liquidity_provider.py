from core.agent.fundamental import FundamentalTrackingAgent
from core.message import MessageType, MessageQueue, Message, new_message
from typing import List

import numpy as np


class LiquidityProviderAgent(FundamentalTrackingAgent):

    def __init__(
        self,
        id,
        lambda_0,
        C_lambda,
        alpha,
        delta_s,
        q_provider=0.5,
        initial_stocks=None,
        *args,
        **kwargs,
    ):
        super().__init__(id, *args, initial_stocks=initial_stocks, **kwargs)
        self.lambda_0 = lambda_0
        self.C_lambda = C_lambda
        self.alpha = alpha
        self.q_provider = q_provider
        self.delta_s = delta_s

        self.time_step = 1
        self.subscribed_stocks: List[str] = (initial_stocks or [])[:]
        self.selected_stocks = list(
            np.random.choice(
                initial_stocks, int(np.random.randint(1, 3)), replace=False
            )
        )
        self.q_taker_values = {}
        for stock in self.selected_stocks:
            self.q_taker_values[stock] = {}

    def action(self):
        super().action()

        requests = []
        for stock in self.selected_stocks:
            # get eta
            eta = self._get_eta(t=self.time_step, stock=stock)
            u = np.random.rand()
            best_bid, best_ask = self._get_best_bid_ask()
            is_buyer = False
            if u < self.q_provider:
                price = best_ask - 1 - eta  # place a limit buy order
                is_buyer = True
            else:
                price = best_bid + 1 + eta  # place a limit sell order

            order = {
                "type": "limit_order",
                "stock": stock,
                "agent_id": self.id,
                "timestamp": str(self.current_time),
                "side": "buy" if is_buyer else "sell",
                "quantity": 1,
                "price": price,
            }
            requests.append(order)

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

        # timestamp increment
        self.time_step += 1

    def _get_eta(self, t, stock):
        u = np.random.rand()
        lambda_t = self._get_lambda_t(t, stock)
        return np.floor(-lambda_t * np.log(u))

    def _get_lambda_t(self, t, stock):
        MC_result = self._MC_simulations(t)
        return self.lambda_0 * (
            1
            + self.C_lambda * np.abs(self.q_taker(t, stock) - 0.5) / np.sqrt(MC_result)
        )

    def _MC_simulations(self, t, stock):
        q = self.q_taker
        result_array = []
        for _ in range(1e5):
            q_t = q(t, stock)
            result_array.append((q_t - 0.5) ** 2)
        return np.average(result_array)

    def q_taker(self, t, stock: str):
        if t == 0:
            return self._update_q_taker_values(t=t, value=0.5, stock=stock)
        prev_q_taker = self.q_taker_values[stock][t - 1]
        u = np.random.rand()
        if u < 0.5:
            result = prev_q_taker + self.delta_s
        else:
            result = prev_q_taker + self.delta_s
        reversion_prob = 0.5 + np.abs(result - 0.5)
        v = np.random.rand()
        if v < reversion_prob:
            if result > 0.5:
                result -= self.delta_s
            elif result < 0.5:
                result += self.delta_s
        return self._update_q_taker_values(t=t, value=result, stock=stock)

    def _update_q_taker_values(self, t, value, stock):
        self.q_taker_values[stock].setdefault(key=str(t), default=value)
        return value

    def _get_best_bid_ask(self):
        msg = self.build_top_of_book_query(stocks=self.selected_stocks)
        self.send(msg)
        msg_in = self.message_queue.get_raw()
        if msg_in.message_type == MessageType.QUERY_TOP_OF_BOOK:
            content = msg_in.content
            best_bid = content["best bid"]
            best_ask = content["best ask"]
        return best_bid, best_ask

    def process_inbox(self):
        super().process_inbox()
