import pandas as pd

from core.kernel import Kernel
from core.orderbook import LimitOrderBook
from core.agent.obi import OrderBookImbalanceAgent
from core.order import LimitOrder


def test_obi_agent_query_then_order():
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
    # Seed book with one level so QUERY_SPERAD returns data
    lob.add_order(LimitOrder(agent_id="seed", timestamp=str(t0), side="sell", quantity=100, price=50.5))
    lob.add_order(LimitOrder(agent_id="seed", timestamp=str(t0), side="buy", quantity=100, price=50.0))
    k.exchange.lob_dict["AAA"] = lob

    ag = OrderBookImbalanceAgent(id="OBI", logger=k.logger, message_queue=k.message_queue, initial_symbols=["AAA"], depth=1)
    k.agents[ag.id] = ag

    ag.wakeup(t0)
    k.process_messages(max_steps=2000)

    assert any(m.message_type.name in ("ORDER_ACCEPTED", "ORDER_EXECUTED") for m in ag.inbox)

