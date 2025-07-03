import pandas as pd
from core.message import MessageQueue, Message, MessageType
from multiprocessing import Process
import pytest
import pandas as pd
from core.message import Message, MessageBox, MessageType, worker_put_message
from queue import PriorityQueue


def test_message_ordering_and_equality():
    t1 = pd.Timestamp("2024-06-25 10:00:00")
    t2 = pd.Timestamp("2024-06-25 10:01:00")
    m1 = Message(
        id="1",
        message_type=MessageType.MESSAGE,
        sender_id="A",
        recipient_id="B",
        send_time=t1,
        recive_time=t1,
    )
    m2 = Message(
        id="2",
        message_type=MessageType.MESSAGE,
        sender_id="A",
        recipient_id="B",
        send_time=t1,
        recive_time=t2,
    )
    assert m1 < m2
    assert m1 != m2
    assert m1 == m1


def test_messagebox_put_and_get():
    box = MessageBox()
    t1 = pd.Timestamp("2024-06-25 10:00:00")
    t2 = pd.Timestamp("2024-06-25 10:01:00")

    m1 = Message(
        id="1",
        message_type=MessageType.MESSAGE,
        sender_id="A",
        recipient_id="B",
        send_time=t1,
        recive_time=t2,
    )
    m2 = Message(
        id="2",
        message_type=MessageType.MESSAGE,
        sender_id="A",
        recipient_id="B",
        send_time=t1,
        recive_time=t1,
    )

    box.put(m1)
    box.put(m2)

    first = box.get()
    second = box.get()

    assert first.id == "2"  # earlier receive time
    assert second.id == "1"
    assert box.empty()


def test_messagebox_iteration_and_length():
    box = MessageBox()
    now = pd.Timestamp.now()

    for i in range(5):
        m = Message(
            id=str(i),
            message_type=MessageType.MESSAGE,
            sender_id="X",
            recipient_id="Y",
            send_time=now,
            recive_time=now + pd.Timedelta(seconds=i),
        )
        box.put(m)

    assert len(box) == 5
    ids = [m.id for m in box]
    assert ids == ["0", "1", "2", "3", "4"]
    assert box.empty()


def test_messagequeue_multiprocess_ordering():
    queue = MessageQueue()
    t0 = pd.Timestamp.now()

    m1 = Message(
        id="1",
        message_type=MessageType.MESSAGE,
        sender_id="P1",
        recipient_id="Kernel",
        send_time=t0,
        recive_time=t0 + pd.Timedelta(seconds=5),
    )

    m2 = Message(
        id="2",
        message_type=MessageType.MESSAGE,
        sender_id="P2",
        recipient_id="Kernel",
        send_time=t0,
        recive_time=t0 + pd.Timedelta(seconds=2),
    )

    p1 = Process(target=worker_put_message, args=(queue, m1, 100))
    p2 = Process(target=worker_put_message, args=(queue, m2, 50))

    p1.start()
    p2.start()
    p1.join()
    p2.join()

    # Simulate Kernel side
    pq = PriorityQueue()
    while not queue.empty_raw():
        msg = queue.get_raw()
        pq.put((msg.recive_time, msg))

    msgs = []
    while not pq.empty():
        _, m = pq.get()
        msgs.append(m)

    assert len(msgs) == 2
    assert msgs[0].id == "2"
    assert msgs[1].id == "1"
