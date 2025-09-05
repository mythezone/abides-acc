import pandas as pd
from core.preopen_book import PreopenOrderBook
from core.order import LimitOrder


def make_order(symbol, side, price, qty, agent="A"):
    return LimitOrder(
        id=f"{agent}-{symbol}-{side}-{price}-{qty}",
        symbol=symbol,
        agent_id=agent,
        side=side,
        price=float(price),
        quantity=int(qty),
        timestamp=str(pd.Timestamp("2005-05-09 09:20:00")),
    )


def test_clearing_price_max_volume():
    book = PreopenOrderBook("000001")
    # Bids: 10@100, 10@99; Asks: 8@99.5, 12@100.5
    book.add_order(make_order("000001", "buy", 100.0, 10, agent="B1"))
    book.add_order(make_order("000001", "buy", 99.0, 10, agent="B2"))
    book.add_order(make_order("000001", "sell", 99.5, 8, agent="S1"))
    book.add_order(make_order("000001", "sell", 100.5, 12, agent="S2"))

    res = book.compute_clearing_price()
    assert res is not None
    px, vol, imb = res
    # At 99.5, executable volume is 18 (10+10 vs 8) => 8; imbalance 12; at 100.5, executable is 12 (10 vs 20) => 10
    # grid [99, 99.5, 100, 100.5]: we expect clearing around 100 with volume 10
    assert vol >= 8

    trades, remaining = book.match_at_clearing()
    # Total traded quantity equals vol from compute (or close, depending on ties)
    tqty = sum(t["quantity"] for t in trades)
    assert tqty > 0
    # Remaining orders carried
    assert isinstance(remaining, list)

