import pandas as pd
import numpy as np

from typing import List, TYPE_CHECKING
from core.message import Message, MessageType

if TYPE_CHECKING:
    from core.kernel import Kernel


class Agent:
    def __init__(
        self,
        id,
        *args,
        kernel: "Kernel" = None,
        location: List[float] = None,
        **kwargs,
    ):
        self.id = id
        self.kernel = kernel
        self.inbox = []
        self.args = args

        if location:
            self.location = location
        else:
            self.location = np.random.uniform(-180, 180, size=2).tolist()

        for key, value in kwargs.items():
            setattr(self, key, value)

    def send(self, message: Message, delay=0):
        self.kernel.send_message(message, delay=delay)

    def wakeup_delay(self):
        return np.random.randint(1000, 5000)

    def set_next_wakeup(self):
        delay_ms = self.wakeup_delay()
        wakeup_time = self.kernel.clock.current_time + pd.Timedelta(
            milliseconds=delay_ms
        )
        msg = Message(
            message_type=MessageType.WAKEUP,
            sender_id=self.id,
            recipient_id=self.id,
            send_time=self.kernel.clock.current_time,
            receive_time=wakeup_time,
            content=None,
        )
        self.send(msg)

    def wakeup(self):
        self.set_next_wakeup()

    def receive(self, message: Message):
        self.inbox.append(message)


class ZeroIntelligenceAgent(Agent):
    def wakeup(self):
        side = np.random.choice(["buy", "sell"])
        quantity = np.random.randint(1, 100)
        price = round(np.random.uniform(10, 100), 2)
        symbol = np.random.choice(list(self.kernel.symbols.keys()))
        order_type = np.random.choice(["limit_order", "market_order"])

        order = {
            "type": order_type,
            "symbol": symbol,
            "agent_id": self.id,
            "timestamp": str(self.kernel.clock.current_time),
            "side": side,
            "quantity": quantity,
        }
        if order_type == "limit_order":
            order["price"] = price

        msg = Message(
            message_type=MessageType.ORDER_SUBMIT,
            sender_id=self.id,
            recipient_id="Exchange",
            send_time=self.kernel.clock.current_time,
            content={"requests": [order]},
        )
        self.send(msg)
        self.set_next_wakeup()
