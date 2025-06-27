import pytest
from core.lob import LimitOrderBook
from core.order import LimitOrder, MarketOrder


def test_limit_order_insert_and_snapshot():
    lob = LimitOrderBook("TEST")
    o1 = LimitOrder(agent_id="A1", timestamp="t1", side="buy", quantity=100, price=10.0)
    o2 = LimitOrder(agent_id="A2", timestamp="t2", side="sell", quantity=50, price=11.0)
    lob.add_order(o1)
    lob.add_order(o2)

    snap = lob.snapshot_top_n()
    assert snap["buy"][0][0] == 10.0
    assert snap["buy"][0][1] == 100
    assert snap["sell"][0][0] == 11.0
    assert snap["sell"][0][1] == 50


def test_limit_order_matching():
    lob = LimitOrderBook("TEST")
    buy = LimitOrder(
        agent_id="A1", timestamp="t1", side="buy", quantity=100, price=10.0
    )
    lob.add_order(buy)
    sell = LimitOrder(
        agent_id="A2", timestamp="t2", side="sell", quantity=60, price=9.5
    )
    trades = lob.add_order(sell)
    assert len(trades) == 1
    assert trades[0]["quantity"] == 60
    assert trades[0]["price"] == 10.0
    assert buy.quantity == 40


def test_market_order_matching():
    lob = LimitOrderBook("TEST")
    lob.add_order(
        LimitOrder(agent_id="A1", timestamp="t1", side="sell", quantity=100, price=10.0)
    )
    market_buy = MarketOrder(agent_id="A2", timestamp="t2", side="buy", quantity=60)
    trades = lob.add_order(market_buy)
    assert len(trades) == 1
    assert trades[0]["quantity"] == 60
    assert trades[0]["price"] == 10.0


def test_cancel_order():
    lob = LimitOrderBook("TEST")
    order = LimitOrder(
        agent_id="A1", timestamp="t1", side="buy", quantity=100, price=9.5
    )
    lob.add_order(order)
    lob.cancel_order(order.id)
    assert order.id not in lob.order_map
