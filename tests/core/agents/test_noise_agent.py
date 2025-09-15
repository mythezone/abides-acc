import pandas as pd

from core.kernel import Kernel
from core.lob import LimitOrderBook
from core.agent.noise import NoiseAgent


def test_noise_agent_sends_orders():
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

    ag = NoiseAgent(id="A", logger=k.logger, message_queue=k.message_queue, initial_symbols=["AAA"])
    k.agents[ag.id] = ag

    t0 = pd.Timestamp("2025-01-02 09:30:00")
    ag.wakeup(t0)
    k.process_messages(max_steps=1000)

    # Should have received at least ORDER_ACCEPTED back
    assert any(m.message_type.name == "ORDER_ACCEPTED" for m in ag.inbox)
