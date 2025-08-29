from core.agent.base import BaseAgent
from core.message import MessageType, MessageQueue, new_message
from typing import List
import numpy as np
import pandas as pd


class ZeroIntelligenceAgent(BaseAgent):

    def __init__(self, id, *args, message_queue: MessageQueue = None, **kwargs):
        super().__init__(id, *args, message_queue=message_queue, **kwargs)
        self.subscribed_symbols: List[str] = []

    def action(self):
        if not self.subscribed_symbols:
            n = int(np.random.randint(1, 5))
            request = {"type": "query_symbols", "n": n}
            msg = new_message(
                message_type=MessageType.MKT_DATA,
                sender_id=self.id,
                recipient_id="Exchange",
                send_time=self.current_time,
                recive_time=self.current_time,
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

                msg = new_message(
                    message_type=MessageType.SUBMIT_ORDER,
                    sender_id=self.id,
                    recipient_id="Exchange",
                    send_time=self.current_time,
                    recive_time=self.current_time,
                    content={"requests": [order]},
                )
                self.send(msg)

    def process_inbox(self):
        # very simple inbox processor: pick up symbol list if provided
        new_symbols = []
        keep = []
        for m in self.inbox:
            if m.message_type == MessageType.MKT_DATA and isinstance(m.content, dict):
                if "symbols" in m.content:
                    new_symbols.extend(m.content.get("symbols", []))
            else:
                keep.append(m)
        self.inbox = keep
        if new_symbols:
            # Deduplicate
            uniq = list(dict.fromkeys(new_symbols))
            self.subscribed_symbols = uniq
