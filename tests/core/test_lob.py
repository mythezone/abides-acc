import pytest

from core.lob import LimitOrderBook
from core.order import LimitOrder, MarketOrder


def make_limit(agent, ts, side, qty, price, id_=None):
    data = {
        "agent_id": agent,
        "timestamp": ts,
        "side": side,
        "quantity": qty,
        "price": price,
    }
    if id_ is not None:
        data["id"] = id_
    return LimitOrder.from_dict(data)


def make_market(agent, ts, side, qty, depth=None, id_=None):
    data = {
        "agent_id": agent,
        "timestamp": ts,
        "side": side,
        "quantity": qty,
    }
    if depth is not None:
        data["market_depth"] = depth
    if id_ is not None:
        data["id"] = id_
    return MarketOrder.from_dict(data)


def test_snapshot_aggregates_per_price_level():
    lob = LimitOrderBook("TEST")
    lob.add_order(make_limit("A", "t1", "buy", 100, 10.0))
    lob.add_order(make_limit("B", "t2", "buy", 50, 10.0))
    lob.add_order(make_limit("C", "t3", "sell", 40, 10.5))
    lob.add_order(make_limit("D", "t4", "sell", 80, 11.1))

    snap = lob.snapshot_top_n(2)
    assert snap["buy"] == [(10.0, 150)]
    assert snap["sell"] == [(10.5, 40), (11.1, 80)]

    csv_line = lob.format_snapshot_csv(n=2)
    # AskPrice0,AskPrice1,AskVolume0,AskVolume1,BidPrice0,BidPrice1,BidVolume0,BidVolume1
    assert csv_line.split(",")[0:4] == ["10.50", "11.10", "40", "80"]


def test_price_time_priority_in_matching():
    lob = LimitOrderBook("TEST")
    early = make_limit("A", "09:30:00.000", "sell", 50, 10.0, id_="E")
    late = make_limit("B", "09:30:00.500", "sell", 50, 10.0, id_="L")
    lob.add_order(early)
    lob.add_order(late)

    buy = make_limit("C", "09:30:01.000", "buy", 70, 10.5)
    trades = lob.add_order(buy)

    assert [t["sell"] for t in trades] == ["A", "B"]
    assert trades[0]["quantity"] == 50
    assert trades[1]["quantity"] == 20


def test_market_order_depth_limit():
    lob = LimitOrderBook("TEST")
    lob.add_order(make_limit("S1", "t1", "sell", 10, 10.0))
    lob.add_order(make_limit("S2", "t2", "sell", 20, 10.1))
    lob.add_order(make_limit("S3", "t3", "sell", 30, 10.2))

    market = make_market("B", "t4", "buy", 100, depth=2)
    trades = lob.add_order(market)

    assert sum(t["quantity"] for t in trades) == 30
    # Only the first two price levels should be consumed
    assert {t["price"] for t in trades} == {10.0, 10.1}
    assert market.quantity == 70  # Remaining because depth exhausted


def test_cancel_order_removes_from_book():
    lob = LimitOrderBook("TEST")
    order = make_limit("A", "t1", "buy", 100, 9.5, id_="OID")
    lob.add_order(order)
    assert "OID" in lob.order_map
    assert lob.cancel_order("OID") is True
    assert "OID" not in lob.order_map
    assert lob.snapshot_top_n()["buy"] == []


def test_ohlc_updates_with_trades():
    lob = LimitOrderBook("TEST")
    lob.add_order(make_limit("S1", "t1", "sell", 50, 10.0))
    lob.add_order(make_limit("S2", "t2", "sell", 50, 9.8))

    lob.add_order(make_limit("B", "t3", "buy", 80, 10.5))
    ohlc = lob.ohlc
    assert ohlc["open"] == pytest.approx(9.8)
    assert ohlc["high"] == pytest.approx(10.0)
    assert ohlc["low"] == pytest.approx(9.8)
    assert ohlc["close"] == pytest.approx(10.0)
    assert ohlc["volume"] == 80
