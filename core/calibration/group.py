from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence, Tuple, Optional

import pandas as pd


@dataclass(order=True)
class CalibratingAgentSpec:
    name: str
    max_order_qty: int
    min_order_qty: int = 1
    price_offset: float = 0.0  # optional price adjustment (ticks)

    def create_order(self, symbol: str, side: str, price: float, quantity: int, timestamp: pd.Timestamp) -> Dict:
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        return {
            "type": "limit_order",
            "agent_id": f"Calibrator_{self.name}",
            "timestamp": str(timestamp),
            "side": side,
            "quantity": int(quantity),
            "price": round(float(price) + float(self.price_offset), 4),
            "symbol": symbol,
            "_exempt_t1": True,
        }


def _to_price_key(price: float) -> str:
    return f"{float(price):.2f}"


def compute_lob_diff(
    real_lob: Dict[str, List[Tuple[float, int]]],
    sim_lob: Dict[str, List[Tuple[float, int]]],
    *,
    max_levels: int = 10,
) -> List[Dict[str, object]]:
    """Compute per-price differences between real and simulated LOB.

    Returns a list of dicts with keys: side, price, quantity, action_side (buy/sell order side).
    """

    def _build_map(levels: List[Tuple[float, int]], reverse: bool = False) -> Dict[str, int]:
        mapping: Dict[str, int] = {}
        for price, qty in levels[:max_levels]:
            if qty <= 0:
                continue
            key = _to_price_key(-price if reverse else price)
            mapping[key] = mapping.get(key, 0) + int(qty)
        return mapping

    real_bids = _build_map(real_lob.get("buy", []), reverse=True)
    real_asks = _build_map(real_lob.get("sell", []), reverse=False)
    sim_bids = _build_map(sim_lob.get("buy", []), reverse=True)
    sim_asks = _build_map(sim_lob.get("sell", []), reverse=False)

    diffs: List[Dict[str, object]] = []

    def _diff_for_side(real_map: Dict[str, int], sim_map: Dict[str, int], side: str):
        keys = set(real_map.keys()) | set(sim_map.keys())
        for key in sorted(keys):
            real_qty = real_map.get(key, 0)
            sim_qty = sim_map.get(key, 0)
            if real_qty == sim_qty:
                continue
            delta = real_qty - sim_qty
            price = float(key)
            if side == "buy":
                price = -price
            if delta > 0:
                action_side = side
                quantity = delta
            else:
                action_side = "sell" if side == "buy" else "buy"
                quantity = -delta
            diffs.append({
                "side": side,
                "price": round(abs(price), 2),
                "quantity": int(quantity),
                "order_side": action_side,
            })

    _diff_for_side(real_bids, sim_bids, "buy")
    _diff_for_side(real_asks, sim_asks, "sell")

    return diffs


class AgentGroup:
    def __init__(
        self,
        exchange,
        oracle,
        agents: Sequence[CalibratingAgentSpec],
        *,
        max_levels: int = 10,
        symbols: Optional[Sequence[str]] = None,
    ) -> None:
        self.exchange = exchange
        self.oracle = oracle
        self.agents = sorted(agents, key=lambda a: a.max_order_qty, reverse=True)
        self.max_levels = max_levels
        self._symbol_filter = set(str(s) for s in symbols) if symbols else None

    def calibrate(self, current_time: pd.Timestamp) -> List[Dict]:
        orders: List[Dict] = []
        if self._symbol_filter is not None:
            symbols = [sym for sym in self._symbol_filter if sym in self.exchange.lob_dict]
        else:
            symbols = list(self.exchange.lob_dict.keys())
        for symbol in symbols:
            if hasattr(self.oracle, "has_lob") and not self.oracle.has_lob(symbol):
                continue
            real_lob = self.oracle.get_lob(symbol, current_time)
            if real_lob is None:
                continue
            sim_lob = self._get_sim_lob(symbol)
            diffs = compute_lob_diff(real_lob, sim_lob, max_levels=self.max_levels)
            orders.extend(self._allocate_orders(symbol, diffs, current_time))
        return orders

    def _get_sim_lob(self, symbol: str) -> Dict[str, List[Tuple[float, int]]]:
        lob = self.exchange.lob_dict.get(symbol)
        if lob is None:
            return {"buy": [], "sell": []}
        buy_levels = lob.snapshot_top_n(self.max_levels)["buy"]
        sell_levels = lob.snapshot_top_n(self.max_levels)["sell"]
        return {"buy": buy_levels, "sell": sell_levels}

    def _allocate_orders(
        self,
        symbol: str,
        diffs: List[Dict[str, object]],
        current_time: pd.Timestamp,
    ) -> List[Dict]:
        generated: List[Dict] = []
        for diff in diffs:
            remaining = int(diff["quantity"])
            order_side = str(diff["order_side"])
            price = float(diff["price"])
            for agent in self.agents:
                if remaining <= 0:
                    break
                max_qty = int(agent.max_order_qty)
                min_qty = int(agent.min_order_qty)
                while remaining >= max_qty:
                    generated.append(
                        agent.create_order(symbol, order_side, price, max_qty, current_time)
                    )
                    remaining -= max_qty
                if remaining >= min_qty:
                    generated.append(
                        agent.create_order(symbol, order_side, price, remaining, current_time)
                    )
                    remaining = 0
                    break
            if remaining > 0:
                # fallback: last agent handles the residue regardless of min
                agent = self.agents[-1]
                generated.append(
                    agent.create_order(symbol, order_side, price, remaining, current_time)
                )
        return generated
