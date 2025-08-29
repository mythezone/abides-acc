import pandas as pd
import numpy as np

from typing import List, TYPE_CHECKING
from core.message import Message, MessageType, MessageQueue, new_message
from typing import Optional
from core.logger import Logger
from core.portfolio import Portfolio
import json

if TYPE_CHECKING:
    from core.kernel import Kernel


class BaseAgent:
    def __init__(
        self,
        id,
        *args,
        message_queue: MessageQueue = None,
        logger: Optional[Logger] = None,
        location: List[float] = None,
        **kwargs,
    ):
        self.id = id
        self.message_queue = message_queue
        self.inbox = []
        self.args = args
        self.current_time = None
        self.logger = logger
        initial_cash = float(kwargs.pop("initial_cash", 1_000_000))
        self.portfolio = Portfolio(initial_cash=initial_cash)

        if location:
            self.location = location
        else:
            self.location = np.random.uniform(-180, 180, size=2).tolist()

        for key, value in kwargs.items():
            setattr(self, key, value)

    def send(self, message: Message, delay=0):
        # Align with MessageQueue.put(message, recive_delay=...)
        if self.logger:
            # Log the sending event (stage=SEND)
            self.logger.kernel_message_log(message, stage="SEND")
        self.message_queue.put(message, recive_delay=delay)

    def wakeup_delay(self):
        rng = getattr(self, "wakeup_ms_range", None)
        if rng and isinstance(rng, (list, tuple)) and len(rng) == 2:
            lo, hi = int(rng[0]), int(rng[1])
            hi = max(hi, lo + 1)
            return int(np.random.randint(lo, hi))
        return int(np.random.randint(1000, 5000))

    def set_next_wakeup(self, current_time, intelver: int = -1):
        if intelver < 0:
            intelver = self.wakeup_delay()

        wakeup_time = current_time + pd.Timedelta(milliseconds=intelver)
        msg = new_message(
            message_type=MessageType.WAKEUP,
            sender_id=self.id,
            recipient_id=self.id,
            send_time=current_time,
            recive_time=wakeup_time,
            content={},
        )
        self.send(msg)

    def process_inbox(self):
        # default handler: update portfolio on executions
        remaining = []
        for m in self.inbox:
            if m.message_type == MessageType.ORDER_EXECUTED and isinstance(m.content, dict):
                trades = m.content.get("trades", [])
                for t in trades:
                    symbol = t.get("symbol")
                    price = float(t.get("price", 0.0))
                    qty = int(t.get("quantity", 0))
                    # Determine if this agent is buyer or seller in this trade
                    if t.get("buy") == self.id:
                        self.portfolio.apply_trade(symbol, "buy", price, qty)
                    if t.get("sell") == self.id:
                        self.portfolio.apply_trade(symbol, "sell", price, qty)
                # After applying, log snapshot
                if self.logger:
                    tv = self.portfolio.current_total_value()
                    self.logger.agent_log(
                        self.id,
                        m.recive_time,
                        cash=self.portfolio.cash,
                        total_value=tv,
                        positions=self.portfolio.holdings,
                    )
            else:
                remaining.append(m)
        self.inbox = remaining

    def action(self):
        pass

    def wakeup(self, current_time):
        self.current_time = current_time
        self.set_next_wakeup(current_time)
        self.process_inbox()
        self.action()
        return

    def receive(self, message: Message):
        self.inbox.append(message)
