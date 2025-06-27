import pytest
from core.order import Order, LimitOrder, MarketOrder


def test_limit_order_creation():
    order = LimitOrder(
        agent_id="agent_1",
        timestamp="2024-06-25 10:00:00",
        side="buy",
        quantity=100,
        price=12.34,
    )
    assert order.agent_id == "agent_1"
    assert order.timestamp == "2024-06-25 10:00:00"
    assert order.side == "buy"
    assert order.quantity == 100
    assert order.price == 12.34
    assert isinstance(order.id, int)


def test_market_order_creation():
    order = MarketOrder(
        agent_id="agent_2", timestamp="2024-06-25 10:01:00", side="sell", quantity=50
    )
    assert order.agent_id == "agent_2"
    assert order.timestamp == "2024-06-25 10:01:00"
    assert order.side == "sell"
    assert order.quantity == 50
    assert isinstance(order.id, int)


def test_order_id_uniqueness():
    ids = set()
    for _ in range(100):
        o = LimitOrder(agent_id="a", timestamp="t", side="buy", quantity=1, price=1.0)
        assert o.id not in ids
        ids.add(o.id)


def test_order_from_dict_limit():
    data = {
        "type": "limit_order",
        "agent_id": "agent_3",
        "timestamp": "2024-06-25 10:02:00",
        "side": "buy",
        "quantity": 10,
        "price": 99.99,
    }
    order = LimitOrder.from_dict(data)
    assert isinstance(order, LimitOrder)
    assert order.price == 99.99


def test_order_from_dict_market():
    data = {
        "type": "market_order",
        "agent_id": "agent_4",
        "timestamp": "2024-06-25 10:03:00",
        "side": "sell",
        "quantity": 25,
    }
    order = MarketOrder.from_dict(data)
    assert isinstance(order, MarketOrder)
    assert order.quantity == 25
