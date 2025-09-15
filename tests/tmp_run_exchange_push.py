import pandas as pd
from core.kernel import Kernel
from core.message import new_message, MessageType
from core.lob import LimitOrderBook


class DummyAgent:
    def __init__(self, id):
        self.id = id
        self.inbox = []

    def receive(self, message):
        self.inbox.append(message)

    def wakeup(self, current_time):
        pass


def main():
    cfg = {
        "name": "compat",
        "start_date": "2025-01-02 09:30:00",
        "trading_days": ["2025-01-02"],
        "exchange_type": "SZSE",
        "exchange_params": {
            "ohlc_freq": "3s",
            "lob_log_level": 3,
            "lob_log_freq": "3s",
            "workers": 0,
        },
    }
    k = Kernel(config=cfg)
    k.initialize()
    for s in ["AAA", "BBB", "CCC"]:
        k.exchange.lob_dict[s] = LimitOrderBook(s)
    k.agents["tester"] = DummyAgent("tester")

    now = pd.Timestamp("2025-01-02 09:30:01")
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

    sub = new_message(
        message_type=MessageType.MKT_DATA_SUBSCRIPTION_REQUEST,
        sender_id="tester",
        recipient_id="Exchange",
        send_time=now,
        recive_time=now,
        content={"subscriptions": [{"symbol": "AAA", "depth": 1, "freq_ms": 0}]},
    )
    k.message_queue.put(sub)

    tick = new_message(
        message_type=MessageType.LOG_TICK,
        sender_id="Kernel",
        recipient_id="Exchange",
        send_time=now + pd.Timedelta(seconds=1),
        recive_time=now + pd.Timedelta(seconds=1),
        content={},
    )
    k.message_queue.put(tick)

    k.process_messages(max_steps=1000)
    msgs = k.agents["tester"].inbox
    print("types:", [m.message_type for m in msgs])
    print("has MKT_DATA:", any(m.message_type == MessageType.MKT_DATA for m in msgs))


if __name__ == "__main__":
    main()

