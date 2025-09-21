from core.agent.fundamental import FundamentalTrackingAgent
from core.message import MessageType, MessageQueue, Message, new_message
from typing import List

import numpy as np


class LiquidityTakerAgent(FundamentalTrackingAgent):

    def __init__(
        self,
        id,
        delta_s,
        mu,
        initial_symbols=None,
        *args,
        **kwargs,
    ):
        super().__init__(id, *args, initial_symbols=initial_symbols, **kwargs)
        self.delta_s = delta_s
        self.mu = mu

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
            q = self.q_taker(t=self.time_step)
            u = np.random.rand()
            is_buyer = True if u < q else False
            order = {
                "type": "market_order",
                "symbol": symbol,
                "agent_id": self.id,
                "timestamp": str(self.current_time),
                "side": "buy" if is_buyer else "sell",
                "quantity": 1,
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

    def q_taker(self, t, symbol: str):
        if t == 0:
            return self._update_q_taker_values(t=t, value=0.5, symbol=symbol)
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
        return self._update_q_taker_values(t=t, value=result, symbol=symbol)

    def _update_q_taker_values(self, t, value, symbol):
        self.q_taker_values[symbol].setdefault(key=str(t), default=value)
        return value

    def _get_best_bid_ask(self):
        msg = self.build_top_of_book_query(symbols=self.selected_symbols)
        self.send(msg)
        msg_in = self.message_queue.get_raw()
        if msg_in.message_type == MessageType.QUERY_TOP_OF_BOOK:
            content = msg_in.content
            best_bid = content["best bid"]
            best_ask = content["best ask"]
        return best_bid, best_ask
