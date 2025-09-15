import pandas as pd

from core.kernel import Kernel
from core.lob import LimitOrderBook
from core.agent.value import ValueAgent


def test_value_agent_order_flow():
    cfg = {
        "name": "a",
        "start_date": "2025-01-02 09:30:00",
        "trading_days": ["2025-01-02"],
        "exchange_type": "SZSE",
        "exchange_params": {"workers": 0, "lob_log_level": 1},
    }
    k = Kernel(config=cfg)
    k.initialize()
    k.exchange.lob_dict["AAA"] = LimitOrderBook("AAA")

    ag = ValueAgent(id="V", logger=k.logger, message_queue=k.message_queue, initial_symbols=["AAA"])
    k.agents[ag.id] = ag

    t0 = pd.Timestamp("2025-01-02 09:30:00")
    ag.wakeup(t0)
    k.process_messages(max_steps=1000)

    assert any(m.message_type.name in ("ORDER_ACCEPTED", "ORDER_EXECUTED") for m in ag.inbox)
