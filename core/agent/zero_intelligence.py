from core.agent.base import BaseAgent
from core.message import Message, MessageType, MessageQueue
from typing import List
import numpy as np
import pandas as pd
from core.portfolio import Portfolio


class ZeroIntelligenceAgent(BaseAgent):

    def __init__(self, id, *args, message_queue: MessageQueue = None, **kwargs):
        super().__init__(id, *args, message_queue=message_queue, **kwargs)
        self.subscribed_symbols: List[str] = []
        self.portfolio = Portfolio()

    def action(self):
        if not self.subscribed_symbols:
            n = np.random.randint(1, 5)
            request = {"type": "query_symbols", "n": n}
            msg = Message(
                message_type=MessageType.MKT_DATA,
                sender_id=self.id,
                recipient_id="Exchange",
                send_time=self.current_time,
                receive_time=self.current_time,
                content=request,
            )
            self.send(msg)
        else:
            k = np.random.randint(1, len(self.subscribed_symbols) + 1)
            selected = np.random.choice(self.subscribed_symbols, k, replace=False)
            for symbol in selected:
                side = np.random.choice(["buy", "sell"])
                quantity = np.random.randint(1, 100)
                price = round(np.random.uniform(10, 100), 2)
                order_type = np.random.choice(["limit_order", "market_order"])

                order = {
                    "type": order_type,
                    "symbol": symbol,
                    "agent_id": self.id,
                    "timestamp": str(self.current_time),
                    "side": side,
                    "quantity": quantity,
                }
                if order_type == "limit_order":
                    order["price"] = price

                msg = Message(
                    message_type=MessageType.SUBMIT_ORDER,
                    sender_id=self.id,
                    recipient_id="Exchange",
                    send_time=self.current_time,
                    receive_time=self.current_time,
                    content={"requests": [order]},
                )
                self.send(msg)
