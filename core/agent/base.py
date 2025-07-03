import pandas as pd
import numpy as np

from typing import List, TYPE_CHECKING
from core.message import Message, MessageType, MessageQueue

if TYPE_CHECKING:
    from core.kernel import Kernel


class BaseAgent:
    def __init__(
        self,
        id,
        *args,
        message_queue: MessageQueue = None,
        location: List[float] = None,
        **kwargs,
    ):
        self.id = id
        self.message_queue = message_queue
        self.inbox = []
        self.args = args
        self.current_time = None

        if location:
            self.location = location
        else:
            self.location = np.random.uniform(-180, 180, size=2).tolist()

        for key, value in kwargs.items():
            setattr(self, key, value)

    def send(self, message: Message, delay=0):
        self.message_queue.put((message, delay))

    def wakeup_delay(self):
        return np.random.randint(1000, 5000)

    def set_next_wakeup(self, current_time, intelver: int = -1):
        if intelver < 0:
            intelver = self.wakeup_delay()

        wakeup_time = current_time + pd.Timedelta(milliseconds=intelver)
        msg = Message(
            message_type=MessageType.WAKEUP,
            sender_id=self.id,
            recipient_id=self.id,
            send_time=current_time,
            receive_time=wakeup_time,
            content=None,
        )
        self.send(msg)

    def process_inbox(self):
        pass

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
