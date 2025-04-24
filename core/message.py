from enum import Enum, unique
import pandas as pd

from core.base import Trackable
from functools import total_ordering
from queue import PriorityQueue


@unique
class MessageType(Enum):
    MESSAGE = 0
    SIMULATION_START = 1
    SIMULATION_END = 2
    WAKEUP = 3

    # Order related messages
    LMT_ORDER = 10
    MKT_ORDER = 11
    CANCEL_ORDER = 12
    MODIFY_ORDER = 13

    ORDER_ACCEPTED = 14
    ORDER_CANCELLED = 15
    ORDER_EXECUTED = 16
    ORDER_SUBMITTED = 17
    ORDER_MODIFIED = 18

    # Market related messages
    MKT_OPEN = 20
    MKT_CLOSE = 21
    MKT_DATA = 22

    # Information related messages
    # WHEN_MKT_OPEN = 30
    # WHEN_MKT_CLOSE = 31
    QUERY_LAST_TRADE = 32
    QUERY_SPERAD = 33
    QUERY_ORDER_STREAM = 34
    QUERY_TRANSACTED_VOLUME = 35
    MKT_DATA_SUBSCRIPTION_REQUEST = 36
    MKT_DATA_SUBSCRIPTION_CANCELLATION = 37

    def __lt__(self, other):
        return self.value < other.value


@total_ordering
class Message(Trackable):

    def __init__(
        self,
        mtype: MessageType = MessageType.MESSAGE,
        sender_id: int = None,
        recipient_id: int = None,
        send_time: pd.Timestamp = None,
        recive_time: pd.Timestamp = None,
        content: dict = {},
    ):
        super().__init__()

        self.message_type = mtype
        self.sender_id = sender_id
        self.recipient_id = recipient_id
        self.send_time = send_time
        self.recive_time = recive_time

        self.content = content

    def __lt__(self, other):
        return self.recive_time < other.recive_time

    def __eq__(self, other):
        return self.id == other.id

    def __str__(self):
        # Make a printable representation of this message.
        return f"{self.content}"

    def make_market_order(self, symbol_name: str, quantity: int, is_buy_order: bool):
        content = {
            "symbol_name": symbol_name,
            "quantity": quantity,
            "is_buy_order": is_buy_order,
        }
        self.content = content


class MessageBox:
    def __init__(self, recive_delay=0):
        self.messages = PriorityQueue()
        self.recive_delay = recive_delay

    def put(self, message: Message, recive_delay=None):
        if not recive_delay:
            recive_delay = self.recive_delay
        message.recive_time = message.recive_time + pd.Timedelta(recive_delay)
        self.messages.put(message)

    def get(self) -> Message:
        if not self.messages.empty():
            return self.messages.get()
        else:
            return None

    def empty(self) -> bool:
        return self.messages.empty()

    def __iter__(self):
        while not self.empty():
            yield self.get()

    def __len__(self):
        return self.messages.qsize()
