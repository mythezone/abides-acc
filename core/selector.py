from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple

import pandas as pd

from core.message import MessageType, new_message


@dataclass
class WeightSnapshot:
    timestamp: pd.Timestamp
    market_cap: Dict[str, float] = field(default_factory=dict)
    volume: Dict[str, float] = field(default_factory=dict)
    uniform: Dict[str, float] = field(default_factory=dict)


class SymbolSelectionManager:
    """Maintains stock sampling distributions and schedules periodic refresh."""

    def __init__(self, exchange, update_interval: str = "60s") -> None:
        self.exchange = exchange
        try:
            self.update_interval = pd.Timedelta(update_interval)
        except Exception:
            self.update_interval = pd.Timedelta(seconds=60)

        self.snapshot: Optional[WeightSnapshot] = None
        self._initialized = False
        self._next_update: Optional[pd.Timestamp] = None

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def initialize(self, now: pd.Timestamp) -> None:
        if self._initialized:
            return
        self.refresh(now)
        self._initialized = True
        self._schedule_next(now)

    def refresh(self, now: pd.Timestamp) -> None:
        stocks = list(self.exchange.stocks)
        market_caps: Dict[str, float] = {}
        volumes: Dict[str, float] = {}
        uniform: Dict[str, float] = {}

        for sym in stocks:
            meta = self.exchange.stock_metadata.get(sym, {})
            try:
                cap = float(meta.get("market_cap", 0.0))
            except Exception:
                cap = 0.0
            market_caps[sym] = max(cap, 0.0)

            try:
                vol = float(self.exchange._stock_volume.get(sym, 0.0))
            except Exception:
                vol = 0.0
            volumes[sym] = max(vol, 0.0)

            uniform[sym] = 1.0

        self.snapshot = WeightSnapshot(
            timestamp=now,
            market_cap=self._normalise(market_caps),
            volume=self._normalise(volumes),
            uniform=self._normalise(uniform),
        )

    def schedule_update(self, when: pd.Timestamp) -> None:
        self._next_update = when
        msg = new_message(
            message_type=MessageType.SYMBOL_SELECTOR_UPDATE,
            sender_id="Exchange",
            recipient_id="Exchange",
            send_time=when,
            recive_time=when,
            content={},
        )
        if self.exchange.logger is not None:
            try:
                self.exchange.logger.kernel_message_log(msg, stage="SEND")
            except Exception:
                pass
        if self.exchange.out_queue is not None:
            self.exchange.out_queue.put(msg)

    def handle_update_message(self, now: pd.Timestamp) -> None:
        self.refresh(now)
        self._schedule_next(now)

    def sample(self, params: Dict, now: pd.Timestamp) -> List[str]:
        if not self._initialized:
            self.initialize(now)
        snapshot = self.snapshot
        if snapshot is None or not snapshot.uniform:
            return []

        strategy = str(params.get("strategy", "random")).lower()
        count = max(int(params.get("count", 1) or 1), 1)
        exclude_param = params.get("exclude") or []
        if isinstance(exclude_param, (str, int)):
            exclude = {str(exclude_param)}
        else:
            exclude = {str(sym) for sym in exclude_param if isinstance(sym, (str, int))}

        weights = self._weights_for_strategy(snapshot, strategy)
        return self._weighted_sample(weights, count, exclude)

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #
    def _schedule_next(self, now: pd.Timestamp) -> None:
        if self.update_interval.total_seconds() <= 0:
            return
        next_time = now + self.update_interval
        self.schedule_update(next_time)

    @staticmethod
    def _normalise(weights: Dict[str, float]) -> Dict[str, float]:
        filtered = {sym: max(float(w), 0.0) for sym, w in weights.items()}
        total = sum(filtered.values())
        if total <= 0:
            # fall back to uniform
            n = len(filtered)
            if n == 0:
                return {}
            return {sym: 1.0 / n for sym in filtered}
        return {sym: w / total for sym, w in filtered.items()}

    def _weights_for_strategy(
        self, snapshot: WeightSnapshot, strategy: str
    ) -> Dict[str, float]:
        if strategy in ("market_cap", "large_cap"):
            weights = snapshot.market_cap
        elif strategy in ("volume", "liquidity"):
            weights = snapshot.volume
        elif strategy in ("small_cap", "inverse_market_cap"):
            if snapshot.market_cap:
                inv = {sym: (1.0 / w) if w > 0 else 0.0 for sym, w in snapshot.market_cap.items()}
                weights = self._normalise(inv)
            else:
                weights = snapshot.uniform
        else:
            weights = snapshot.uniform

        if weights:
            return weights
        return snapshot.uniform

    def _weighted_sample(
        self, weights: Dict[str, float], requested: int, exclude: Iterable[str]
    ) -> List[str]:
        remaining = [(sym, w) for sym, w in weights.items() if sym not in exclude and w > 0]
        if not remaining:
            remaining = [(sym, 1.0) for sym in weights if sym not in exclude]
        if not remaining:
            return []

        rand_fn = random.random
        rng = getattr(self.exchange, "random_generator", None)
        if rng is not None:
            try:
                candidate = rng()
                if hasattr(candidate, "random"):
                    rand_fn = candidate.random
            except TypeError:
                if hasattr(rng, "random"):
                    rand_fn = rng.random

        selected: List[str] = []
        pool = remaining.copy()
        while pool and len(selected) < requested:
            total_weight = sum(w for _, w in pool)
            r = rand_fn() * total_weight
            cumulative = 0.0
            picked_index = 0
            for idx, (_, weight) in enumerate(pool):
                cumulative += weight
                if cumulative >= r:
                    picked_index = idx
                    break
            sym, _ = pool.pop(picked_index)
            selected.append(sym)
        if len(selected) < requested:
            leftovers = [sym for sym, _ in pool]
            random.shuffle(leftovers)
            selected.extend(leftovers[: requested - len(selected)])
        return selected
