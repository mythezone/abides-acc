from core.agent.fundamental import FundamentalTrackingAgent
from core.message import MessageType, MessageQueue, new_message
from typing import List, Optional

import numpy as np
import pandas as pd


class NearZeroIntelligenceAgent(FundamentalTrackingAgent):

    def __init__(
        self,
        id,
        message_queue: MessageQueue = None,
        initial_symbols: Optional[List[str]] = None,
        alpha=0.85,
        kappa=4.10,
        phi=0.016,
        period_limit=5,
        *args,
        **kwargs,
    ):
        super().__init__(
            id,
            *args,
            message_queue=message_queue,
            initial_symbols=initial_symbols,
            **kwargs,
        )
        self.subscribed_symbols: List[str] = (initial_symbols or [])[:]

        self.alpha = alpha
        self.kappa = kappa
        self.phi = phi
        self.period_limit = period_limit

        self.current_period = 0
        self.prev_avg_price = 0

    def action(self):
        super().action()
        selected_symbols = list(
            np.random.choice(
                self.subscribed_symbols, int(np.random.randint(1, 3)), replace=False
            )
        )

        for symbol in selected_symbols:
            requests = []

            # make the trading decision
            is_buyer = self._determine_buyer_rule(symbol=symbol)

            # get fundamental values
            fundamental_value = self._get_fundamental_price()

            # get transaction price
            price = self._generate_price(
                is_buyer=is_buyer, fundamental_value=fundamental_value
            )

            # generate size
            # Since the paper doesn't speicfy how to generate order size, here I just follow the implementation in ZeroIntellugenceAgent.
            inventory = int(self.portfolio.holdings.get(symbol, 0))
            quantity = int(np.random.randint(1, 50))
            if not is_buyer and inventory > 0:
                quantity = max(1, min(quantity, inventory))

            # add content to contents
            order = {
                "type": "limit_order",
                "symbol": symbol,
                "agent_id": self.id,
                "timestamp": str(self.current_time),
                "side": "buy" if is_buyer else "sell",
                "quantity": quantity,
                "price": price,
            }
            requests.append(order)

        # when the for loop ends, submit the orders once
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

        # self.current_period increment
        self.current_period += 1
        if self.current_period > self.period_limit:
            self._end_period()

    def _determine_buyer_rule(self, symbol) -> bool:
        """Return true if it is a buyer."""
        p = np.random.rand()
        pi_t = np.max(0.5 - self.phi * self.current_period, 0)
        is_buyer = p < pi_t
        # check if we have the current stock
        inventory = int(self.portfolio.holdings.get(symbol, 0))
        if not is_buyer and inventory == 0:
            is_buyer = True
        return is_buyer

    def _get_fundamental_price(self):
        """Return the current fundamental prices."""
        pass

    def _generate_price(self, is_buyer: bool, fundamental_value):
        """Generate the market price, based on fundamental value."""
        u = np.random.uniform(0, self.kappa * fundamental_value)  # random component
        price = (1 - self.alpha) * u + self.alpha * self.prev_avg_price

        if is_buyer:
            price = np.min([price, self.portfolio.cash])
        return np.round(price, 2)

    def _end_period(self):
        self.current_period=0
        pass
