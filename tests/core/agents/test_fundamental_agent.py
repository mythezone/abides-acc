import pandas as pd

from core.kernel import Kernel
from core.orderbook import LimitOrderBook
from core.agent.fundamental import FundamentalTrackingAgent


def test_fundamental_agent_orders():
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

    ag = FundamentalTrackingAgent(id="FT", logger=k.logger, message_queue=k.message_queue, initial_symbols=["AAA"])
    k.agents[ag.id] = ag

    t0 = pd.Timestamp("2025-01-02 09:30:00")
    ag.wakeup(t0)
    k.process_messages(max_steps=2000)

    assert any(m.message_type.name in ("ORDER_ACCEPTED", "ORDER_EXECUTED") for m in ag.inbox)

