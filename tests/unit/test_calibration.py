import pandas as pd

from core.calibration.group import AgentGroup, CalibratingAgentSpec, compute_lob_diff


class DummyLOB:
    def __init__(self, bids, asks):
        self._bids = bids
        self._asks = asks

    def snapshot_top_n(self, n):
        return {
            "buy": self._bids[:n],
            "sell": self._asks[:n],
        }


class DummyExchange:
    def __init__(self, lob_dict):
        self.lob_dict = lob_dict


class DummyOracle:
    def __init__(self, lob_by_symbol):
        self.lob_by_symbol = lob_by_symbol

    def get_lob(self, symbol, current_time):
        return self.lob_by_symbol.get(symbol)


def test_compute_lob_diff_basic():
    real = {"buy": [(10.0, 100), (9.9, 80)], "sell": [(10.1, 90)]}
    sim = {"buy": [(10.0, 60)], "sell": [(10.1, 120)]}
    diffs = compute_lob_diff(real, sim)
    assert {d["price"] for d in diffs} == {10.0, 10.1}
    buy_diff = next(d for d in diffs if d["price"] == 10.0)
    assert buy_diff["order_side"] == "buy"
    assert buy_diff["quantity"] == 40
    sell_diff = next(d for d in diffs if d["price"] == 10.1)
    assert sell_diff["order_side"] == "buy"
    assert sell_diff["quantity"] == 30


def test_agent_group_greedy_allocation():
    exchange = DummyExchange(
        {
            "XYZ": DummyLOB(bids=[(10.0, 50)], asks=[(10.1, 50)]),
        }
    )
    oracle = DummyOracle(
        {
            "XYZ": {"buy": [(10.0, 150)], "sell": [(10.1, 10)]}
        }
    )
    agents = [
        CalibratingAgentSpec(name="Large", max_order_qty=60, min_order_qty=30),
        CalibratingAgentSpec(name="Medium", max_order_qty=20, min_order_qty=10),
        CalibratingAgentSpec(name="Small", max_order_qty=5, min_order_qty=1),
    ]
    group = AgentGroup(exchange, oracle, agents)
    orders = group.calibrate(pd.Timestamp("2024-01-01 09:30:00"))
    # Buy side needs +100, sell side needs -40 -> 40 sell orders -> we expect orders for both sides
    buy_orders = [o for o in orders if o["side"] == "buy"]
    sell_orders = [o for o in orders if o["side"] == "sell"]
    assert sum(o["quantity"] for o in buy_orders) == 100
    assert sum(o["quantity"] for o in sell_orders) == 40
    # ensure greedy allocation uses large agent first
    large_orders = [o for o in orders if o["agent_id"] == "Calibrator_Large"]
    assert any(o["quantity"] == 60 for o in large_orders)
    # residue handled by medium/small
    assert any(o["agent_id"] == "Calibrator_Small" for o in orders)
