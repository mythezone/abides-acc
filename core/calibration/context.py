from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence, Optional

import pandas as pd

from core.calibration.group import AgentGroup, CalibratingAgentSpec


from typing import Iterable, List, Sequence, Optional, Union


def _build_agent_specs(raw_specs: Iterable[Union[dict, CalibratingAgentSpec]]) -> List[CalibratingAgentSpec]:
    specs: List[CalibratingAgentSpec] = []
    for spec in raw_specs or ():
        if isinstance(spec, CalibratingAgentSpec):
            specs.append(spec)
            continue
        if not isinstance(spec, dict):
            continue
        try:
            specs.append(
                CalibratingAgentSpec(
                    name=str(spec.get("name", f"A{len(specs)}")),
                    max_order_qty=int(spec.get("max_order_qty", 1)),
                    min_order_qty=int(spec.get("min_order_qty", 1)),
                    price_offset=float(spec.get("price_offset", 0.0)),
                )
            )
        except Exception:
            continue
    if not specs:
        # Provide a minimal fallback to ensure calibration can proceed
        specs = [
            CalibratingAgentSpec(name="Large", max_order_qty=5000, min_order_qty=1000),
            CalibratingAgentSpec(name="Medium", max_order_qty=1000, min_order_qty=200),
            CalibratingAgentSpec(name="Small", max_order_qty=200, min_order_qty=1),
        ]
    return specs


def _normalize_offset(value) -> pd.Timedelta:
    if isinstance(value, pd.Timedelta):
        return value
    if isinstance(value, (int, float)):
        return pd.Timedelta(milliseconds=float(value))
    try:
        return pd.Timedelta(str(value))
    except Exception:
        return pd.Timedelta(milliseconds=10)


@dataclass
class CalibrationContext:
    exchange: object
    oracle: object
    agent_specs: Iterable[Union[dict, CalibratingAgentSpec]]
    stocks: Optional[Sequence[str]] = None
    max_levels: int = 10
    trigger_offset: Union[pd.Timedelta, int, float, str] = pd.Timedelta(milliseconds=10)

    def __post_init__(self) -> None:
        specs = _build_agent_specs(self.agent_specs)
        self.trigger_offset = _normalize_offset(self.trigger_offset)
        normalized_stocks = self._normalize_stocks(self.stocks)
        self.agent_group = AgentGroup(
            self.exchange,
            self.oracle,
            specs,
            max_levels=int(self.max_levels),
            stocks=normalized_stocks,
        )

    @staticmethod
    def _normalize_stocks(stocks: Optional[Sequence[str]]) -> Optional[List[str]]:
        if not stocks:
            return None
        normalized: List[str] = []
        for sym in stocks:
            if isinstance(sym, str):
                normalized.append(sym)
            elif isinstance(sym, dict):
                val = sym.get("stock")
                if val:
                    normalized.append(str(val))
        return normalized or None

    def calibrate(self, current_time: pd.Timestamp) -> List[dict]:
        return self.agent_group.calibrate(current_time)
