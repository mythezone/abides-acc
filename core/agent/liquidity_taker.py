from core.agent.fundamental import FundamentalTrackingAgent
from core.message import MessageType, MessageQueue, Message, new_message
from typing import List

import numpy as np


class LiquidityTakerAgent(FundamentalTrackingAgent):

    def __init__(
        self,
        id,
        lambda_0,
        C_lambda,
        alpha,
        delta_s,
        q_provider=0.5,
        initial_symbols=None,
        *args,
        **kwargs,
    ):
        super().__init__(id, *args, initial_symbols=initial_symbols, **kwargs)
        self.lambda_0 = lambda_0
        self.C_lambda = C_lambda
        self.alpha = alpha
        self.q_provider = q_provider
        self.delta_s = delta_s

        self.time_step = 1
        self.subscribed_symbols: List[str] = (initial_symbols or [])[:]
        self.selected_symbols = list(
            np.random.choice(
                initial_symbols, int(np.random.randint(1, 3)), replace=False
            )
        )
        self.q_taker_values = {}
        for symbol in self.selected_symbols:
            self.q_taker_values[symbol] = {}

    def action(self):
        super().action()

        requests = []
        for symbol in self.selected_symbols:
            # get eta
            eta = self._get_eta(t=self.time_step, symbol=symbol)
            u = np.random.rand()
            best_bid, _, best_ask, _ = self.getKnownBidAsk(
                symbol=self.symbol, best=True
            )
            is_buyer = False
            if u < self.q_provider:
                price = best_ask - 1 - eta  # place a limit buy order
                is_buyer = True
            else:
                price = best_bid + 1 + eta  # place a limit sell order

            order = {
                "type": "limit_order",
                "symbol": symbol,
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

    def _get_eta(self, t, symbol):
        u = np.random.rand()
        lambda_t = self._get_lambda_t(t, symbol)
        return np.floor(-lambda_t * np.log(u))

    def _get_lambda_t(self, t, symbol):
        MC_result = self._MC_simulations(t)
        return self.lambda_0 * (
            1
            + self.C_lambda * np.abs(self.q_taker(t, symbol) - 0.5) / np.sqrt(MC_result)
        )

    def _MC_simulations(self, t, symbol):
        q = self.q_taker
        result_array = []
        for _ in range(1e5):
            q_t = q(t, symbol)
            result_array.append((q_t - 0.5) ** 2)
        return np.average(result_array)

    def q_taker(self, t, symbol: str):
        if t == 0:
            return 0.5
        prev_q_taker = self.q_taker_values[symbol][t - 1]
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
        return result

    def _make_order(self, eta, symbol):
        u = np.random.rand()
        best_bid, _, best_ask, _ = self.getKnownBidAsk(symbol=self.symbol, best=True)
        is_buy_order = False
        if u < self.q_provider:
            price = best_ask - 1 - eta  # place a limit buy order
            is_buy_order = True
        else:
            price = best_bid + 1 + eta  # place a limit sell order

        self.placeLimitOrder(
            symbol=self.symbol, quantity=1, is_buy_order=is_buy_order, limit_price=price
        )

    def getKnownBidAsk(self, symbol, best):
        pass
