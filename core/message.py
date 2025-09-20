from multiprocessing import Queue
from enum import Enum, unique
import pandas as pd
from functools import total_ordering
from dataclasses import dataclass, field
from queue import PriorityQueue
from typing import Any, Dict, Optional
from uuid import uuid4
from queue import Empty


def worker_put_message(queue, msg, delay):
    queue.put(msg, recive_delay=delay)


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
    SUBMIT_ORDER = 14

    ORDER_ACCEPTED = 15
    ORDER_CANCELLED = 16
    ORDER_EXECUTED = 17
    ORDER_SUBMITTED = 18
    ORDER_MODIFIED = 19

    # Market related messages
    MKT_OPEN = 20
    MKT_CLOSE = 21
    MKT_DATA = 22

    QUERY_LAST_TRADE = 32
    QUERY_SPERAD = 33
    QUERY_ORDER_STREAM = 34
    QUERY_TRANSACTED_VOLUME = 35
    MKT_DATA_SUBSCRIPTION_REQUEST = 36
    MKT_DATA_SUBSCRIPTION_CANCELLATION = 37
    QUERY_FUNDAMENTAL = 38
    QUERY_TOP_OF_BOOK = 39

    LOG_LOB = 40
    LOG_OHLC = 41
    LOG_TICK = 42

    # Oracle related
    ORACLE_QUERY_LOB = 50
    ORACLE_QUERY_OHLC = 51
    ORACLE_RESPONSE_LOB = 52
    ORACLE_RESPONSE_OHLC = 53


@total_ordering
@dataclass
class Message:
    id: str
    message_type: MessageType
    sender_id: str
    recipient_id: str
    send_time: pd.Timestamp
    recive_time: pd.Timestamp
    content: Dict[str, Any] = field(default_factory=dict)

    def __lt__(self, other: "Message"):
        return self.recive_time < other.recive_time

    def __eq__(self, other: "Message"):
        return self.id == other.id

    def __str__(self):
        return (
            f"Message(id={self.id}, type={self.message_type}, content={self.content})"
        )


class MessageBox:
    def __init__(self, recive_delay=0):
        self.messages = PriorityQueue()
        self.recive_delay = recive_delay

    def put(self, message: Message, recive_delay=None):
        if recive_delay is None:
            recive_delay = self.recive_delay
        adjusted_time = message.recive_time + pd.Timedelta(milliseconds=recive_delay)
        adjusted_message = Message(
            id=message.id,
            message_type=message.message_type,
            sender_id=message.sender_id,
            recipient_id=message.recipient_id,
            send_time=message.send_time,
            recive_time=adjusted_time,
            content=message.content,
        )
        self.messages.put(adjusted_message)

    def get(self) -> Optional[Message]:
        if not self.messages.empty():
            m = self.messages.get()
            return m
        return None

    def empty(self) -> bool:
        return self.messages.empty()

    def __iter__(self):
        while not self.empty():
            yield self.get()

    def __len__(self):
        return self.messages.qsize()


class MessageQueue:
    def __init__(self):
        self.mp_queue = Queue()

    def put(self, message: Message, recive_delay=0):
        adjusted_time = message.recive_time + pd.Timedelta(milliseconds=recive_delay)
        # Avoid copying content for performance; messages should be treated as immutable
        adjusted_message = Message(
            id=message.id,
            message_type=message.message_type,
            sender_id=message.sender_id,
            recipient_id=message.recipient_id,
            send_time=message.send_time,
            recive_time=adjusted_time,
            content=message.content,
        )
        self.mp_queue.put(adjusted_message)

    def get_raw(self):
        # Directly retrieve from raw multiprocessing queue
        return self.mp_queue.get()

    def empty_raw(self):
        return self.mp_queue.empty()

    def get_nowait_raw(self):
        return self.mp_queue.get_nowait()


def new_message(
    *,
    message_type: MessageType,
    sender_id: str,
    recipient_id: str,
    send_time: pd.Timestamp,
    recive_time: Optional[pd.Timestamp] = None,
    content: Optional[Dict[str, Any]] = None,
) -> Message:
    """Helper to create a Message with a generated id and default recive_time.

    Ensures consistent field names (recive_time) across the codebase.
    """
    if recive_time is None:
        recive_time = send_time
    return Message(
        id=str(uuid4()),
        message_type=message_type,
        sender_id=sender_id,
        recipient_id=recipient_id,
        send_time=send_time,
        recive_time=recive_time,
        content=content or {},
    )
