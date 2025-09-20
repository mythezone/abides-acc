import pandas as pd

from core.agent.base import BaseAgent
from core.kernel import Kernel
from core.message import new_message, MessageType


class DummyAgent:
    def __init__(self, id):
        self.id = id
        self.inbox = []

    def receive(self, message):
        self.inbox.append(message)

    def wakeup(self, current_time):
        pass


def _make_kernel():
    cfg = {
        "name": "compat",
        "start_date": "2025-01-02 09:30:00",
        "trading_days": ["2025-01-02"],
        "exchange_type": "SZSE",
        "exchange_params": {"ohlc_freq": "3s", "lob_log_level": 3, "lob_log_freq": "3s", "workers": 0},
    }
    k = Kernel(config=cfg)
    k.initialize()
    # seed some symbols
    for s in ["AAA", "BBB", "CCC"]:
        if s not in k.exchange.lob_dict:
            from core.lob import LimitOrderBook

            k.exchange.lob_dict[s] = LimitOrderBook(s)
    # register dummy receiver
    k.agents["tester"] = DummyAgent("tester")
    return k


def test_abides_compat_message_flow():
    k = _make_kernel()
    now = pd.Timestamp("2025-01-02 09:30:01")

    # 1) Batch submit with two sides that cross on AAA
    reqs = [
        {
            "type": "limit_order",
            "symbol": "AAA",
            "agent_id": "tester",
            "timestamp": str(now),
            "side": "buy",
            "quantity": 100,
            "price": 50.0,
        },
        {
            "type": "limit_order",
            "symbol": "AAA",
            "agent_id": "tester",
            "timestamp": str(now),
            "side": "sell",
            "quantity": 100,
            "price": 50.0,
        },
        {
            "type": "market_order",
            "symbol": "BBB",
            "agent_id": "tester",
            "timestamp": str(now),
            "side": "buy",
            "quantity": 10,
        },
    ]
    msg = new_message(
        message_type=MessageType.SUBMIT_ORDER,
        sender_id="tester",
        recipient_id="Exchange",
        send_time=now,
        recive_time=now,
        content={"requests": reqs},
    )
    k.message_queue.put(msg)
    k.process_messages()

    # 2) Modify an order on CCC
    # Place a resting order
    place = new_message(
        message_type=MessageType.SUBMIT_ORDER,
        sender_id="tester",
        recipient_id="Exchange",
        send_time=now,
        recive_time=now,
        content={
            "requests": [
                {
                    "type": "limit_order",
                    "symbol": "CCC",
                    "agent_id": "tester",
                    "timestamp": str(now),
                    "side": "buy",
                    "quantity": 50,
                    "price": 10.0,
                    "id": 9991,
                }
            ]
        },
    )
    k.message_queue.put(place)
    # Modify it
    mod = new_message(
        message_type=MessageType.MODIFY_ORDER,
        sender_id="tester",
        recipient_id="Exchange",
        send_time=now,
        recive_time=now,
        content={
            "requests": [
                {
                    "symbol": "CCC",
                    "order_id": 9991,
                    "new_order": {
                        "type": "limit_order",
                        "symbol": "CCC",
                        "agent_id": "tester",
                        "timestamp": str(now),
                        "side": "buy",
                        "quantity": 50,
                        "price": 11.0,
                    },
                }
            ]
        },
    )
    k.message_queue.put(mod)
    k.process_messages()

    # 3) Cancel remaining CCC order
    cancel = new_message(
        message_type=MessageType.CANCEL_ORDER,
        sender_id="tester",
        recipient_id="Exchange",
        send_time=now,
        recive_time=now,
        content={"requests": [{"symbol": "CCC", "order_id": 9991}]},
    )
    k.message_queue.put(cancel)
    k.process_messages()

    # 4) Queries
    q1 = new_message(
        message_type=MessageType.QUERY_LAST_TRADE,
        sender_id="tester",
        recipient_id="Exchange",
        send_time=now,
        recive_time=now,
        content={"symbol": "AAA"},
    )
    q2 = new_message(
        message_type=MessageType.QUERY_SPERAD,
        sender_id="tester",
        recipient_id="Exchange",
        send_time=now,
        recive_time=now,
        content={"symbol": "AAA", "depth": 1},
    )
    q3 = new_message(
        message_type=MessageType.QUERY_ORDER_STREAM,
        sender_id="tester",
        recipient_id="Exchange",
        send_time=now,
        recive_time=now,
        content={"symbol": "AAA", "length": 5},
    )
    q4 = new_message(
        message_type=MessageType.QUERY_TRANSACTED_VOLUME,
        sender_id="tester",
        recipient_id="Exchange",
        send_time=now,
        recive_time=now,
        content={"symbol": "AAA", "lookback_period": "5m"},
    )
    for m in [q1, q2, q3, q4]:
        k.message_queue.put(m)
    k.process_messages()

    # 5) Market data subscription and tick push
    sub = new_message(
        message_type=MessageType.MKT_DATA_SUBSCRIPTION_REQUEST,
        sender_id="tester",
        recipient_id="Exchange",
        send_time=now,
        recive_time=now,
        content={"subscriptions": [{"symbol": "AAA", "depth": 1, "freq_ms": 0}]},
    )
    k.message_queue.put(sub)
    # trigger tick
    tick = new_message(
        message_type=MessageType.LOG_TICK,
        sender_id="Kernel",
        recipient_id="Exchange",
        send_time=now + pd.Timedelta(seconds=1),
        recive_time=now + pd.Timedelta(seconds=1),
        content={},
    )
    k.message_queue.put(tick)
    for _ in range(3):
        res = k.process_messages()
        if res.get("processed", 0) > 0:
            break

    # Basic sanity: ensure tester received something from each phase
    msgs = [m for m in k.agents["tester"].inbox]
    kinds = {m.message_type for m in msgs}
    assert MessageType.ORDER_ACCEPTED in kinds
    assert MessageType.ORDER_EXECUTED in kinds
    assert MessageType.QUERY_LAST_TRADE in kinds
    assert MessageType.QUERY_SPERAD in kinds
    assert MessageType.QUERY_ORDER_STREAM in kinds
    assert MessageType.QUERY_TRANSACTED_VOLUME in kinds
    assert any(m.message_type == MessageType.MKT_DATA for m in msgs)


def test_exchange_multi_symbol_queries():
    k = _make_kernel()
    now = pd.Timestamp("2025-01-02 09:35:00")
    agent = k.agents["tester"]

    # Seed resting liquidity for two symbols so queries have data to return.
    for idx, symbol in enumerate(["AAA", "BBB"]):
        ts = now + pd.Timedelta(milliseconds=idx)
        submit = new_message(
            message_type=MessageType.SUBMIT_ORDER,
            sender_id="tester",
            recipient_id="Exchange",
            send_time=ts,
            recive_time=ts,
            content={
                "requests": [
                    {
                        "type": "limit_order",
                        "symbol": symbol,
                        "agent_id": "tester",
                        "timestamp": str(ts),
                        "side": "buy",
                        "quantity": 10,
                        "price": 49.0 + idx,
                    },
                    {
                        "type": "limit_order",
                        "symbol": symbol,
                        "agent_id": "tester",
                        "timestamp": str(ts),
                        "side": "sell",
                        "quantity": 12,
                        "price": 51.0 + idx,
                    },
                ]
            },
        )
        k.message_queue.put(submit)
    k.process_messages()
    agent.inbox.clear()

    helper = BaseAgent("tester")
    helper.current_time = now + pd.Timedelta(seconds=1)
    fund_msg = helper.build_fundamental_query(["AAA", "BBB"])
    top_msg = helper.build_top_of_book_query(["AAA", "BBB"], depth=1)

    for msg in [fund_msg, top_msg]:
        assert msg is not None
        k.message_queue.put(msg)

    # Drain kernel queue; message propagation through multiprocessing.Queue can
    # require more than one pass, so retry a few times to ensure delivery.
    for _ in range(3):
        res = k.process_messages()
        if res.get("processed", 0) > 0:
            break

    fund_responses = [
        m for m in agent.inbox if m.message_type == MessageType.QUERY_FUNDAMENTAL
    ]
    top_responses = [
        m for m in agent.inbox if m.message_type == MessageType.QUERY_TOP_OF_BOOK
    ]

    assert len(fund_responses) == 2
    assert len(top_responses) == 2

    fund_map = {m.content.get("symbol"): m for m in fund_responses}
    top_map = {m.content.get("symbol"): m for m in top_responses}

    assert fund_map["AAA"].content.get("data") == 50.0
    assert fund_map["BBB"].content.get("data") == 51.0

    assert top_map["AAA"].content.get("best_bid") == 49.0
    assert top_map["AAA"].content.get("best_ask") == 51.0
    assert top_map["BBB"].content.get("best_bid") == 50.0
    assert top_map["BBB"].content.get("best_ask") == 52.0
