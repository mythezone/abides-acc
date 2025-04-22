from enum import Enum, unique
from agent.base import Agent
import pandas as pd

from core.base import Trackable
from functools import total_ordering


@unique
class MessageType(Enum):
    MESSAGE = 0
    WAKEUP = 1

    # Order related messages
    LIMIT_ORDER = 10
    MARKET_ORDER = 11
    CANCEL_ORDER = 12
    MODIFY_ORDER = 13
    ORDER_ACCEPTED = 14
    ORDER_CANCELLED = 15
    ORDER_EXECUTED = 16
    ORDER_SUBMITTED = 17
    ORDER_MODIFIED = 18

    # Market related messages
    MARKET_OPEN = 20
    MARKET_CLOSE = 21
    MARKET_DATA = 22

    # Information related messages
    WHEN_MARKET_OPEN = 30
    WHEN_MARKET_CLOSE = 31
    QUERY_LAST_TRADE = 32
    QUERY_SPERAD = 33
    QUERY_ORDER_STREAM = 34
    QUERY_TRANSACTED_VOLUME = 35
    MARKET_DATA_SUBSCRIPTION_REQUEST = 36
    MARKET_DATA_SUBSCRIPTION_CANCELLATION = 37

    def __lt__(self, other):
        return self.value < other.value


@total_ordering
class Message(Trackable):

    def __init__(
        self,
        mtype: MessageType,
        sender_id: int,
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
        return f"{self.message_type} from {self.sender_id} to {self.recipient_id} at {self.send_time}: {self.content}"
