from multiprocessing import Queue
from enum import Enum, unique
import pandas as pd
from functools import total_ordering
from dataclasses import dataclass, field
from queue import PriorityQueue
from typing import Any, Dict, Optional, List, Tuple
from uuid import uuid4
from queue import Empty
import heapq


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
    QUERY_SPREAD = 33 # spread was misspelled in previous snippets
    QUERY_ORDER_STREAM = 34
    QUERY_TRANSACTED_VOLUME = 35
    MKT_DATA_SUBSCRIPTION_REQUEST = 36
    MKT_DATA_SUBSCRIPTION_CANCELLATION = 37
    QUERY_FUNDAMENTAL = 38
    QUERY_TOP_OF_BOOK = 39

    LOG_LOB = 40
    LOG_OHLC = 41
    LOG_TICK = 42
    SELECT_STOCKS_REQUEST = 43
    SELECT_STOCKS_RESPONSE = 44
    MKT_DATA_SUBSCRIPTION_TICK = 45
    STOCK_SELECTOR_UPDATE = 46

    # Oracle related
    ORACLE_QUERY_LOB = 50
    ORACLE_QUERY_OHLC = 51
    ORACLE_RESPONSE_LOB = 52
    ORACLE_RESPONSE_OHLC = 53

    # Calibration related
    CALIBRATION_TRIGGER = 60
    CALIBRATION_ORDER = 61


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
    def __init__(self, segment_ms: int = 1000):
        # Underlying multiprocessing queue for cross-process and cross-thread safety
        self.mp_queue = Queue()
        # Segment size in milliseconds for bucketing by adjusted recive_time
        try:
            segment_ms_int = int(segment_ms)
        except Exception:
            segment_ms_int = 1000
        if segment_ms_int <= 0:
            segment_ms_int = 1000
        self._segment_ms: int = segment_ms_int
        self._segment_ns: int = self._segment_ms * 1_000_000  # pandas Timestamp.value is ns
        # Per-segment heaps keyed by (time_ns, seq, message)
        self._segments: Dict[int, List[Tuple[int, int, Message]]] = {}
        # Min-heap of active segment keys
        self._segment_keys: List[int] = []
        # Global sequence counter to ensure a stable ordering
        self._seq: int = 0
        # Cached total size for fast emptiness checks
        self._size: int = 0

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

    def _segment_key(self, ts: pd.Timestamp) -> int:
        try:
            ns = int(ts.value)
        except Exception:
            # Fallback: treat invalid timestamps as 0
            ns = 0
        return ns // self._segment_ns if self._segment_ns > 0 else 0

    def _insert_segmented(self, msg: Message) -> None:
        key = self._segment_key(msg.recive_time)
        heap = self._segments.get(key)
        if heap is None:
            heap = []
            self._segments[key] = heap
            heapq.heappush(self._segment_keys, key)
        self._seq += 1
        try:
            time_ns = int(msg.recive_time.value)
        except Exception:
            time_ns = 0
        heapq.heappush(heap, (time_ns, self._seq, msg))
        self._size += 1

    def _drain_mp_queue_nonblocking(self) -> None:
        while True:
            try:
                msg = self.mp_queue.get_nowait()
            except Empty:
                break
            self._insert_segmented(msg)

    def _pop_earliest(self) -> Optional[Message]:
        while self._segment_keys:
            key = self._segment_keys[0]
            heap = self._segments.get(key)
            if not heap:
                heapq.heappop(self._segment_keys)
                self._segments.pop(key, None)
                continue
            _, _, msg = heapq.heappop(heap)
            self._size -= 1
            if not heap:
                heapq.heappop(self._segment_keys)
                self._segments.pop(key, None)
            return msg
        return None

    def get_raw(self):
        # Drain any messages from the underlying multiprocessing queue,
        # then return the globally earliest by recive_time.
        self._drain_mp_queue_nonblocking()
        msg = self._pop_earliest()
        if msg is not None:
            return msg
        # If we have nothing buffered locally, block on the underlying queue
        base_msg = self.mp_queue.get()
        self._insert_segmented(base_msg)
        # Drain any additional messages that might have arrived concurrently
        self._drain_mp_queue_nonblocking()
        msg = self._pop_earliest()
        if msg is None:
            return base_msg
        return msg

    def empty_raw(self):
        self._drain_mp_queue_nonblocking()
        return self._size == 0

    def get_nowait_raw(self):
        self._drain_mp_queue_nonblocking()
        msg = self._pop_earliest()
        if msg is None:
            raise Empty
        return msg


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
