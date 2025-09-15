import pandas as pd

from core.kernel import Kernel
from core.lob import LimitOrderBook
from core.agent.hbl import HeuristicBeliefLearningAgent
from core.order import LimitOrder


def test_hbl_agent_orders():
    cfg = {
        "name": "a",
        "start_date": "2025-01-02 09:30:00",
        "trading_days": ["2025-01-02"],
        "exchange_type": "SZSE",
        "exchange_params": {"workers": 0, "lob_log_level": 1},
    }
    k = Kernel(config=cfg)
    k.initialize()
    t0 = pd.Timestamp("2025-01-02 09:30:00")

    lob = LimitOrderBook("AAA")
    lob.add_order(LimitOrder(agent_id="seed", timestamp=str(t0), side="sell", quantity=100, price=50.5))
    lob.add_order(LimitOrder(agent_id="seed", timestamp=str(t0), side="buy", quantity=100, price=50.0))
    k.exchange.lob_dict["AAA"] = lob

    ag = HeuristicBeliefLearningAgent(id="HBL", logger=k.logger, message_queue=k.message_queue, initial_symbols=["AAA"])
    k.agents[ag.id] = ag

    ag.wakeup(t0)
    k.process_messages(max_steps=2000)

    assert any(m.message_type.name in ("ORDER_ACCEPTED", "ORDER_EXECUTED") for m in ag.inbox)

