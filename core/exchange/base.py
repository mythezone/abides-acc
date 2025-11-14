from core.orderbook import LimitOrderBook
from core.message import MessageType, new_message, Message
from core.ohlc import OHLCAggregator
from core.order import Order, LimitOrder, MarketOrder
import pandas as pd
import numpy as np
import random
import csv
from pathlib import Path


import threading
from queue import Queue
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Dict, Tuple, Iterable, List
from core.preopen_book import PreopenOrderBook
from core.logger import Logger
from util.util import random_china_location, network_latency_ms
from core.selector import StockSelectionManager
from .handler.manager import HandlerManager
from . import handler as _exchange_handlers  # noqa: F401
from core.selector import StockSelectionManager
from .handler.manager import HandlerManager
from . import handler as _exchange_handlers  # noqa: F401


class Exchange:
    """Generic exchange with basic LOB, OHLC logging and optional workers.

    Subclasses may override validation and fee rules.
    """

    def __init__(
        self,
        stocks: Iterable[str],
        logger: Logger,
        ohlc_freq: str = "3s",
        lob_log_level: int = 5,
        lob_log_freq: str = "3s",
        workers: int = 0,
        out_queue=None,
        **kwargs,
    ):
        location_value = kwargs.pop("location", None)
        if location_value is None:
            self.location: Tuple[float, float] = random_china_location()
        else:
            try:
                lat, lon = location_value
                self.location = (float(lat), float(lon))
            except Exception:
                self.location = random_china_location()

        market_cap_range = kwargs.pop("market_cap_range", (5e9, 5e11))
        self.market_cap_range = self._normalize_market_cap_range(market_cap_range)
        self.stocks, self.stock_metadata = self._normalize_stock_specs(stocks)
        self.lob_dict = {
            stock_name: LimitOrderBook(stock_name) for stock_name in self.stocks
        }
        for sym in self.stocks:
            self._ensure_market_cap(sym)
        self.logger = logger
        self.ohlc_freq = ohlc_freq
        self.ohlc_by_stock: dict[str, OHLCAggregator] = {}
        self.lob_log_level = lob_log_level
        # support special tick mode
        self._lob_tick_mode = str(lob_log_freq).lower() == "tick"
        self.lob_log_delta = None if self._lob_tick_mode else pd.Timedelta(lob_log_freq)
        self._last_lob_log: dict[str, pd.Timestamp] = {}
        self._lob_log_initialized = False
        self._next_lob_log_time: Optional[pd.Timestamp] = None
        self.out_queue = out_queue
        self.is_open: bool = True
        # Price references and last prices per stock for limit checks in subclasses
        self._last_price: Dict[str, float] = {}
        # Fee rate in bps (subclasses may override)
        self.fee_rate: float = 0.0  # e.g., 0.0003 = 3 bps
        # Optional initial positions for account-aware rules (agent_id -> {stock: qty})
        self._initial_positions: Dict[str, Dict[str, int]] = {}
        # Track per-agent T+1 availability (agent, stock) -> remaining sellable qty
        self._t1_available: Dict[Tuple[str, str], int] = {}
        # Per-day buy/sell counters for T+1 enforcement (legacy metrics)
        self._day_buys: Dict[Tuple[str, str], int] = {}  # (agent,stock)->qty
        self._day_sells: Dict[Tuple[str, str], int] = {}
        self._stock_volume: Dict[str, int] = {str(sym): 0 for sym in self.stocks}
        self.selector = StockSelectionManager(self, kwargs.pop("selector_update_freq", "60s"))
        self.handler_manager = HandlerManager()

        # Market data subscriptions: agent_id -> stock -> {depth, freq_ms, last_sent}
        self._subs: dict[str, dict[str, dict]] = {}
        self._agent_locations: Dict[str, Tuple[float, float]] = {}

        trade_log_enabled = bool(kwargs.pop("trade_log_enabled", False))
        trade_log_path = kwargs.pop("trade_log_path", None)
        self._trade_log_lock = threading.Lock()
        self.trade_log_enabled = trade_log_enabled
        self.trade_log_path = None
        self._trade_log_file = None
        self._trade_log_writer = None
        self._trade_log_base_time: Optional[pd.Timestamp] = None
        self._trade_log_counter: int = 0
        self.calibration_context = None
        self._calibration_offset = pd.Timedelta(milliseconds=10)
        if self.trade_log_enabled:
            if not trade_log_path:
                raise ValueError("trade_log_path must be provided when trade logging is enabled.")
            self.trade_log_path = Path(trade_log_path).expanduser()
            self.trade_log_path.parent.mkdir(parents=True, exist_ok=True)
            self._trade_log_file = self.trade_log_path.open(
                "w", newline="", encoding="utf-8"
            )
            self._trade_log_writer = csv.writer(self._trade_log_file)
            self._trade_log_writer.writerow(["id", "time", "valume", "price"])

        # Parallel workers sharded by stock hash (if requested)
        self.workers = int(workers) if workers and int(workers) > 0 else 0
        self._worker_queues: list[Queue] = []
        self._executor: Optional[ThreadPoolExecutor] = None
        if self.workers > 0:
            self._executor = ThreadPoolExecutor(
                max_workers=self.workers, thread_name_prefix="exch"
            )
            self._worker_queues = [Queue() for _ in range(self.workers)]
            for idx in range(self.workers):
                self._executor.submit(self._worker_loop, idx)

        # kwargs
        init_snapshots = kwargs.pop("initial_snapshots", None)
        for key, value in kwargs.items():
            setattr(self, key, value)
        if init_snapshots:
            self._apply_initial_snapshots(init_snapshots)

    def _apply_initial_snapshots(self, snapshots):
        if hasattr(snapshots, "items"):
            iterator = snapshots.items()
        elif isinstance(snapshots, dict):
            iterator = snapshots.items()
        else:
            iterator = []
        for stock, path in iterator:
            lob = self._ensure_lob(stock)
            try:
                lob.initialize_from_csv(path, agent_id="InitAgent", timestamp="1970-01-01T00:00:00")
            except Exception:
                pass

    def register_agent_location(
        self, agent_id: str, location: Optional[Iterable[float]]
    ) -> None:
        if not isinstance(agent_id, str) or location is None:
            return
        try:
            lat, lon = location
            self._agent_locations[agent_id] = (float(lat), float(lon))
        except Exception:
            pass

    def _ensure_lob_scheduler(self, now: pd.Timestamp) -> None:
        if self._lob_tick_mode or self.lob_log_delta is None or self.out_queue is None:
            return
        if self._lob_log_initialized:
            return
        anchor = pd.Timestamp(now)
        next_time = anchor.ceil(self.lob_log_delta)
        if next_time < anchor:
            next_time = next_time + self.lob_log_delta
        self._schedule_lob_tick(next_time)
        self._lob_log_initialized = True

    def _schedule_lob_tick(self, when: pd.Timestamp) -> None:
        if self.out_queue is None or self.lob_log_delta is None:
            return
        self._next_lob_log_time = when
        if self.calibration_context is not None:
            self._schedule_calibration_trigger(when)
        msg = new_message(
            message_type=MessageType.LOG_TICK,
            sender_id="Exchange",
            recipient_id="Exchange",
            send_time=when,
            recive_time=when,
            content={"kind": "LOB_SNAPSHOT"},
        )
        if self.logger is not None:
            try:
                self.logger.kernel_message_log(msg, stage="SEND")
            except Exception:
                pass
        self.out_queue.put(msg)

    def _schedule_calibration_trigger(self, log_time: pd.Timestamp) -> None:
        if self.out_queue is None or self.calibration_context is None:
            return
        cal_time = log_time - self._calibration_offset
        if cal_time >= log_time:
            cal_time = log_time
        msg = new_message(
            message_type=MessageType.CALIBRATION_TRIGGER,
            sender_id="Exchange",
            recipient_id="Exchange",
            send_time=cal_time,
            recive_time=cal_time,
            content={"log_time": log_time},
        )
        if self.logger is not None:
            try:
                self.logger.kernel_message_log(msg, stage="SEND")
            except Exception:
                pass
        self.out_queue.put(msg)

    def enable_calibration(self, context) -> None:
        self.calibration_context = context
        if context is None:
            return
        try:
            offset = getattr(context, "trigger_offset", None)
            if offset is not None:
                if not isinstance(offset, pd.Timedelta):
                    offset = pd.Timedelta(offset)
                self._calibration_offset = offset
        except Exception:
            self._calibration_offset = pd.Timedelta(milliseconds=10)

    def _schedule_subscription_tick(
        self, agent_id: str, stock: str, when: pd.Timestamp
    ) -> None:
        if self.out_queue is None:
            return
        msg = new_message(
            message_type=MessageType.MKT_DATA_SUBSCRIPTION_TICK,
            sender_id="Exchange",
            recipient_id="Exchange",
            send_time=when,
            recive_time=when,
            content={"agent_id": agent_id, "stock": stock},
        )
        if self.logger is not None:
            try:
                self.logger.kernel_message_log(msg, stage="SEND")
            except Exception:
                pass
        self.out_queue.put(msg)

    @property
    def initial_positions(self) -> Dict[str, Dict[str, int]]:
        return self._initial_positions

    @initial_positions.setter
    def initial_positions(self, positions: Optional[Dict[str, Dict[str, int]]]):
        self._initial_positions = positions or {}
        self._rebuild_t1_limits()

    def _rebuild_t1_limits(self) -> None:
        self._t1_available.clear()
        for agent, holdings in self._initial_positions.items():
            if not isinstance(holdings, dict):
                continue
            for stock, qty in holdings.items():
                try:
                    self._t1_available[(agent, stock)] = int(qty)
                except Exception:
                    self._t1_available[(agent, stock)] = 0

    def handle_message(self, message: Message):
        now = message.send_time
        self._ensure_lob_scheduler(now)
        if self.logger is not None:
            self.logger.kernel_message_log(message, stage="PROC")
        if message.message_type == MessageType.CALIBRATION_TRIGGER:
            self._handle_calibration_trigger(now, message)
            return []
        return self.handler_manager.handle(self, message, now)


    def _tick_log(self, now: pd.Timestamp):
        self._log_lob_snapshot(now)
        if not self._lob_tick_mode and self.lob_log_delta is not None:
            self._next_lob_log_time = now + self.lob_log_delta
            self._schedule_lob_tick(self._next_lob_log_time)

    def _log_lob_snapshot(self, now: pd.Timestamp) -> None:
        if self.logger is None:
            return
        for stock, lob in self.lob_dict.items():
            sym = str(stock)
            price = None
            snap = lob.snapshot_top_n(1)
            if snap["buy"] and snap["sell"]:
                bid = float(snap["buy"][0][0])
                ask = float(snap["sell"][0][0])
                price = round((bid + ask) / 2.0, 2)
            if price is not None:
                if sym not in self.ohlc_by_stock:
                    self.ohlc_by_stock[sym] = OHLCAggregator(
                        sym, self.ohlc_freq, self.logger
                    )
                self.ohlc_by_stock[sym].update(now, price, volume=0.0)
                self._last_price[sym] = float(price)
            level = self.lob_log_level
            lob_csv = lob.format_snapshot_csv(level)
            self.logger.lob_log(
                stock_name=sym, kernel_time=now, level=level, lob=lob_csv
            )
            self._last_lob_log[sym] = now


    # Exposed helper for kernel to detect preopen (default False)
    def is_preopen_time(self, now: pd.Timestamp) -> bool:
        return False

    # --- Validation and fees hooks ---
    def _validate_order(self, order: Order, now: pd.Timestamp) -> bool:
        """Generic validation: always accept. Subclasses may override."""
        return True

    def _route_preopen(self, order: Order, now: pd.Timestamp) -> bool:
        """Hook for subclasses to route orders to pre-open call auction book.
        Return True if the order was consumed by pre-open logic.
        """
        return False

    def _apply_fees(self, price: float, qty: int) -> float:
        if not self.fee_rate:
            return 0.0
        return float(price) * int(qty) * float(self.fee_rate)

    def _worker_loop(self, idx: int):
        q = self._worker_queues[idx]
        while True:
            item = q.get()
            if item is None:
                # Sentinel received: exit worker loop
                q.task_done()
                break
            now, order = item
            try:
                self._process_order(now, order)
            except Exception:
                pass
            finally:
                q.task_done()

    def _emit(self, msg: Message):
        delay = 0.0
        recipient = getattr(msg, "recipient_id", None)
        if isinstance(recipient, str):
            peer_loc = self._agent_locations.get(recipient)
            if peer_loc is not None:
                delay = network_latency_ms(self.location, peer_loc)
        if self.out_queue is not None:
            self.out_queue.put(msg, recive_delay=delay)

    # --- Stock metadata helpers ---
    def _normalize_market_cap_range(self, raw) -> Tuple[float, float]:
        try:
            lo, hi = raw
            lo = float(lo)
            hi = float(hi)
        except Exception:
            lo, hi = 5e9, 5e11
        if not np.isfinite(lo) or lo < 0:
            lo = 0.0
        if not np.isfinite(hi) or hi <= lo:
            hi = lo * 10 if lo > 0 else lo + 1.0
        return float(lo), float(hi)

    def _normalize_stock_specs(
        self, stocks: Iterable
    ) -> Tuple[List[str], Dict[str, Dict[str, object]]]:
        if stocks is None:
            iterable = []
        elif isinstance(stocks, (str, bytes)):
            iterable = [stocks]
        else:
            iterable = list(stocks)
        names: List[str] = []
        metadata: Dict[str, Dict[str, object]] = {}
        seen = set()
        for entry in iterable:
            stock: Optional[str] = None
            extra: Dict[str, object] = {}
            if isinstance(entry, dict):
                raw_sym = entry.get("stock")
                if raw_sym is None:
                    continue
                stock = str(raw_sym)
                extra = {k: v for k, v in entry.items() if k != "stock"}
            elif entry is None:
                continue
            else:
                stock = str(entry)
            if not stock:
                continue
            if stock not in seen:
                names.append(stock)
                seen.add(stock)
            meta = metadata.setdefault(stock, {})
            if extra:
                meta.update(extra)
        for sym in names:
            metadata.setdefault(sym, {})
        return names, metadata

    def _ensure_market_cap(self, stock: str) -> float:
        meta = self.stock_metadata.setdefault(stock, {})
        current = meta.get("market_cap")
        try:
            cap_val = float(current)
        except Exception:
            cap_val = None
        if cap_val is None or not np.isfinite(cap_val) or cap_val <= 0:
            lo, hi = self.market_cap_range
            cap_val = random.uniform(lo, hi)
        meta["market_cap"] = float(cap_val)
        return float(cap_val)

    def _get_lob(self, stock: Optional[str]) -> Optional[LimitOrderBook]:
        if isinstance(stock, str):
            return self.lob_dict.get(stock)
        return None

    def _ensure_lob(self, stock: Optional[str]) -> Optional[LimitOrderBook]:
        if not isinstance(stock, str):
            return None
        lob = self.lob_dict.get(stock)
        if lob is None:
            lob = LimitOrderBook(stock)
            self.lob_dict[stock] = lob
            if stock not in self.stocks:
                self.stocks.append(stock)
            self.stock_metadata.setdefault(stock, {})
        self._ensure_market_cap(stock)
        self._stock_volume.setdefault(stock, 0)
        return lob

    def _build_strategy_weights(
        self, strategy: str, pool: List[str], params: Dict
    ) -> List[Tuple[str, float]]:
        strat = (strategy or "random").lower()
        weights: List[Tuple[str, float]] = []
        if strat == "random":
            return [(sym, 1.0) for sym in pool]
        if strat in ("market_cap", "large_cap"):
            for sym in pool:
                cap = self.stock_metadata.get(sym, {}).get("market_cap")
                try:
                    weight = float(cap)
                except Exception:
                    weight = 0.0
                weights.append((sym, max(weight, 0.0)))
            return weights
        if strat in ("small_cap", "inverse_market_cap"):
            for sym in pool:
                cap = self.stock_metadata.get(sym, {}).get("market_cap")
                try:
                    cap_val = float(cap)
                except Exception:
                    cap_val = 0.0
                weight = 0.0
                if cap_val > 0:
                    weight = 1.0 / cap_val
                weights.append((sym, weight))
            return weights
        if strat in ("volume", "high_volume", "top_volume"):
            for sym in pool:
                vol = self._stock_volume.get(sym, 0)
                if vol <= 0:
                    lob = self._get_lob(sym)
                    if lob is not None:
                        vol = lob.traded_volume()
                weights.append((sym, float(max(vol, 0))))
            return weights
        if strat in ("low_volume",):
            tmp: List[Tuple[str, float]] = []
            for sym in pool:
                vol = self._stock_volume.get(sym, 0)
                if vol <= 0:
                    lob = self._get_lob(sym)
                    if lob is not None:
                        vol = lob.traded_volume()
                weight = 0.0
                if vol > 0:
                    weight = 1.0 / vol
                tmp.append((sym, weight))
            return tmp
        if strat == "liquidity":
            depth = params.get("depth")
            try:
                depth_val = max(1, int(depth))
            except Exception:
                depth_val = 5
            for sym in pool:
                lob = self._get_lob(sym)
                if lob is None:
                    weights.append((sym, 0.0))
                    continue
                bid_volume = lob.resting_volume("buy", depth_val)
                ask_volume = lob.resting_volume("sell", depth_val)
                weights.append((sym, float(bid_volume + ask_volume)))
            return weights
        if strat == "tight_spread":
            eps = params.get("epsilon", 1e-6)
            try:
                eps = float(eps)
            except Exception:
                eps = 1e-6
            eps = max(eps, 1e-12)
            for sym in pool:
                lob = self._get_lob(sym)
                spread = lob.spread() if lob is not None else None
                if spread is None or spread < 0:
                    weight = 0.0
                else:
                    weight = 1.0 / (spread + eps) if spread + eps > 0 else 0.0
                weights.append((sym, weight))
            return weights
        if strat == "momentum":
            for sym in pool:
                lob = self._get_lob(sym)
                if lob is None:
                    weights.append((sym, 0.0))
                    continue
                open_price = lob.ohlc.get("open")
                close_price = lob.ohlc.get("close")
                if open_price is None or close_price is None:
                    weights.append((sym, 0.0))
                    continue
                change = float(close_price) - float(open_price)
                weights.append((sym, max(change, 0.0)))
            return weights
        if strat in ("bid_pressure", "ask_pressure", "imbalance"):
            depth = params.get("depth")
            try:
                depth_val = max(1, int(depth))
            except Exception:
                depth_val = 5
            for sym in pool:
                lob = self._get_lob(sym)
                if lob is None:
                    weights.append((sym, 0.0))
                    continue
                imbalance = lob.book_imbalance(depth_val)
                if strat == "bid_pressure" or (strat == "imbalance" and imbalance >= 0):
                    weight = max(imbalance, 0.0)
                else:
                    weight = max(-imbalance, 0.0)
                weights.append((sym, weight))
            return weights
        return []

    def _weighted_sample(
        self, weighted_stocks: List[Tuple[str, float]], count: int
    ) -> List[str]:
        pool = []
        for sym, weight in weighted_stocks:
            if not isinstance(sym, str):
                continue
            try:
                w = float(weight)
            except Exception:
                w = 0.0
            if w < 0:
                w = 0.0
            pool.append([sym, w])
        if not pool:
            return []
        unique_count = len(pool)
        if count >= unique_count:
            ordered = sorted(pool, key=lambda item: item[1], reverse=True)
            return [sym for sym, _ in ordered]
        selected: List[str] = []
        while pool and len(selected) < count:
            total_weight = sum(item[1] for item in pool)
            if total_weight <= 0:
                remaining = [item[0] for item in pool]
                random.shuffle(remaining)
                needed = count - len(selected)
                selected.extend(remaining[:needed])
                break
            r = random.uniform(0, total_weight)
            cumulative = 0.0
            for idx, item in enumerate(pool):
                cumulative += item[1]
                if cumulative >= r:
                    selected.append(item[0])
                    pool.pop(idx)
                    break
        return selected


    def _select_stocks(self, params: Dict) -> list[str]:
        if not self.stocks:
            return []
        strategy = str(params.get("strategy", "random"))
        try:
            requested = int(params.get("count", 1))
        except Exception:
            requested = 1
        requested = max(1, requested)
        exclude_param = params.get("exclude") or []
        if isinstance(exclude_param, (str, int)):
            exclude = {str(exclude_param)}
        else:
            exclude = {str(sym) for sym in exclude_param if isinstance(sym, (str, int))}
        pool = [str(sym) for sym in self.stocks if str(sym) not in exclude]
        if not pool:
            return []
        weights = self._build_strategy_weights(strategy, pool, params)
        if not weights:
            weights = self._build_strategy_weights("random", pool, params)
        selection = self._weighted_sample(weights, requested)
        if selection:
            return selection
        random.shuffle(pool)
        return pool[:requested]

    def _process_order(self, now: pd.Timestamp, order: Order):
        stock = (
            getattr(order, "_stock", None) or getattr(order, "stock", None) or None
        )
        if stock is None:
            # fallback from request dict stored in order
            if hasattr(order, "__dict__") and "stock" in order.__dict__:
                stock = order.__dict__["stock"]
        lob = self._ensure_lob(stock)
        if lob is None:
            return

        trades = lob.add_order(order)
        # Acknowledge
        ack = new_message(
            message_type=MessageType.ORDER_ACCEPTED,
            sender_id="Exchange",
            recipient_id=order.agent_id,
            send_time=now,
            recive_time=now,
            content={"order_id": order.id, "stock": str(stock)},
        )
        self._emit(ack)

        if trades:
            # accumulate fee
            total_fee = 0.0
            executed_qty = 0
            for t in trades:
                # track last price
                try:
                    self._last_price[str(stock)] = float(t["price"])  # per our trade dict
                except Exception:
                    pass
                qty = int(t.get("quantity", 0))
                executed_qty += qty
                total_fee += self._apply_fees(t.get("price", 0.0), qty)
            if executed_qty > 0:
                sym_key = str(stock)
                self._stock_volume[sym_key] = int(self._stock_volume.get(sym_key, 0)) + executed_qty
            execmsg = new_message(
                message_type=MessageType.ORDER_EXECUTED,
                sender_id="Exchange",
                recipient_id=order.agent_id,
                send_time=now,
                recive_time=now,
                content={
                    "trades": trades,
                    "stock": str(stock),
                    "fees": round(total_fee, 6),
                },
            )
            self._emit(execmsg)
            self._log_trades(trades, now)

        # OHLC update
        price = None
        if trades:
            price = float(trades[-1]["price"])
        else:
            snap = lob.snapshot_top_n(1)
            if snap["buy"] and snap["sell"]:
                bid = float(snap["buy"][0][0])
                ask = float(snap["sell"][0][0])
                price = round((bid + ask) / 2.0, 2)
        if price is not None and self.logger is not None:
            sym = str(stock)
            if sym not in self.ohlc_by_stock:
                self.ohlc_by_stock[sym] = OHLCAggregator(
                    sym, self.ohlc_freq, self.logger
                )
            self.ohlc_by_stock[sym].update(now, price, volume=float(order.quantity))
            self._last_price[sym] = float(price)

    def _handle_calibration_trigger(self, now: pd.Timestamp, message: Message) -> None:
        if self.calibration_context is None:
            return
        try:
            orders = self.calibration_context.calibrate(now)
        except Exception:
            orders = []
        if not orders:
            return
        for req in orders:
            try:
                self._process_calibration_request(req, now)
            except Exception:
                continue

    def _process_calibration_request(self, req: Dict, now: pd.Timestamp) -> None:
        stock = req.get("stock")
        if not stock:
            return
        self._ensure_lob(stock)
        otype = req.get("type", "limit_order")
        if otype == "limit_order":
            order = LimitOrder.from_dict(req)
        elif otype == "market_order":
            order = MarketOrder.from_dict(req)
        else:
            order = Order.from_dict(req)
        setattr(order, "_stock", stock)
        setattr(order, "_exempt_t1", True)
        if not getattr(order, "agent_id", None):
            order.agent_id = "CalibrationAgent"
        self._process_order(now, order)

    def _log_trades(self, trades: List[dict], now: pd.Timestamp) -> None:
        if not self.trade_log_enabled or self._trade_log_writer is None:
            return
        with self._trade_log_lock:
            if self._trade_log_base_time is None:
                try:
                    self._trade_log_base_time = pd.Timestamp(now)
                except Exception:
                    self._trade_log_base_time = pd.Timestamp.now()
            base = self._trade_log_base_time
            for trade in trades:
                raw_ts = trade.get("timestamp", now)
                try:
                    trade_ts = pd.Timestamp(raw_ts)
                except Exception:
                    trade_ts = pd.Timestamp(now)
                rel_time = (trade_ts - base).total_seconds()
                quantity = float(trade.get("quantity", 0))
                price = float(trade.get("price", 0))
                self._trade_log_counter += 1
                self._trade_log_writer.writerow(
                    [
                        self._trade_log_counter,
                        f"{rel_time:.6f}",
                        f"{quantity:.6f}",
                        f"{price:.5f}",
                    ]
                )
            try:
                self._trade_log_file.flush()
            except Exception:
                pass

    def shutdown(self, wait: bool = True):
        """Gracefully stop background workers and flush aggregators/logs.

        This prevents lingering non-daemon threads from keeping the process alive
        after simulations complete.
        """
        # Flush OHLC aggregators
        try:
            for agg in self.ohlc_by_stock.values():
                agg.flush_all()
        except Exception:
            pass

        # Stop worker threads
        if self.workers > 0:
            try:
                for q in self._worker_queues:
                    # Send sentinel to each worker
                    q.put(None)
            except Exception:
                pass
            if self._executor is not None:
                try:
                    self._executor.shutdown(wait=wait, cancel_futures=False)
                except TypeError:
                    # For older Python versions without cancel_futures
                    self._executor.shutdown(wait=wait)
            # Mark workers disabled
            self.workers = 0
        if self._trade_log_file is not None:
            try:
                self._trade_log_file.flush()
            except Exception:
                pass
            try:
                self._trade_log_file.close()
            except Exception:
                pass
            self._trade_log_file = None
            self._trade_log_writer = None


class SZSExchange(Exchange):
    """SZSE-like rules: optional T+1, price limits, and fees on executions."""

    def __init__(
        self,
        *args,
        t_plus_one: bool = True,
        price_limit_pct: float = 0.1,
        fee_rate: float = 0.0003,
        initial_positions: Optional[Dict[str, Dict[str, int]]] = None,
        initial_snapshots: Optional[Dict[str, str]] = None,
        opening_call: bool = False,
        **kwargs,
    ):
        # opening_call is handled here and not passed to base class
        default_location = kwargs.pop("location", (22.5333, 114.0667))  # Shenzhen
        super().__init__(*args, initial_snapshots=initial_snapshots, location=default_location, **kwargs)
        self.t_plus_one = bool(t_plus_one)
        self.price_limit_pct = float(price_limit_pct) if price_limit_pct else 0.0
        self.fee_rate = float(fee_rate) if fee_rate else 0.0
        self.initial_positions = initial_positions or {}
        # opening call auction placeholders (not fully implemented)
        self.opening_call = bool(opening_call)
        # Pre-open call auction storage
        self._preopen_books: Dict[str, PreopenOrderBook] = {}
        self._auction_done: Dict[str, bool] = {}
        self._preopen_once: set[tuple[str, str]] = set()  # (agent_id, stock)
        self._preopen_last_order_ts: Optional[pd.Timestamp] = None

    @staticmethod
    def _time_only(ts: pd.Timestamp):
        return ts.time() if isinstance(ts, pd.Timestamp) else pd.Timestamp(ts).time()

    def is_preopen_time(self, now: pd.Timestamp) -> bool:
        t = self._time_only(now)
        # 09:15:00 <= t < 09:25:00 (SZSE call auction window)
        return pd.Timestamp("09:15").time() <= t < pd.Timestamp("09:25").time()

    def _route_preopen(self, order: Order, now: pd.Timestamp) -> bool:
        # If within pre-open window, store orders for auction and do not place into LOB
        if not self.opening_call:
            return False
        if not self.is_preopen_time(now):
            return False
        stock = getattr(order, "_stock", None) or getattr(order, "stock", None)
        if stock is None:
            return False
        key = (getattr(order, "agent_id", ""), stock)
        # Allow only one submission per agent per stock during pre-open
        if key in self._preopen_once:
            return True
        self._preopen_once.add(key)
        book = self._preopen_books.setdefault(stock, PreopenOrderBook(stock))
        book.add_order(order)
        self._preopen_last_order_ts = now
        # ACK acceptance
        ack = new_message(
            message_type=MessageType.ORDER_ACCEPTED,
            sender_id="Exchange",
            recipient_id=order.agent_id,
            send_time=now,
            recive_time=now,
            content={"order_id": order.id, "stock": stock, "phase": "preopen"},
        )
        self._emit(ack)
        # Opportunistic preopen snapshot log for this stock
        try:
            self._log_preopen_stock(stock, now)
        except Exception:
            pass
        return True

    def handle_message(self, message: Message):
        # Override to support pre-open cancel and 09:25 auction match
        now = message.send_time
        # 09:25:00 auction matching
        try:
            if self.opening_call and (
                self._time_only(now) >= pd.Timestamp("09:25").time()
            ):
                self._run_call_auction(now)
        except Exception:
            pass
        # 09:15-09:20 allow cancel on preopen book
        if (
            message.message_type == MessageType.CANCEL_ORDER
            and self.opening_call
            and pd.Timestamp("09:15").time()
            <= self._time_only(now)
            < pd.Timestamp("09:20").time()
        ):
            for req in message.content.get("requests", []):
                oid = req.get("order_id")
                for sym, book in self._preopen_books.items():
                    book.cancel_order(oid)
            return []
        # Fallback to base handling (includes preopen routing hook)
        return super().handle_message(message)

    def _run_call_auction(self, now: pd.Timestamp):
        # For each stock, if auction not done and there are preopen orders, determine opening price and match
        for stock, book in list(self._preopen_books.items()):
            if self._auction_done.get(stock, False):
                continue
            snap = book.snapshot_top_n(1)
            # If no book content, mark done
            if not (snap.get("buy") or snap.get("sell")):
                self._auction_done[stock] = True
                continue
            trades, remaining = book.match_at_clearing()
            # Emit executions to both sides (one message per participant)
            # Aggregate per agent for simplicity
            by_agent: Dict[str, list] = {}
            for t in trades:
                by_agent.setdefault(t["buy"], []).append(t)
                by_agent.setdefault(t["sell"], []).append(t)
            for aid, tr in by_agent.items():
                total_fee = sum(self._apply_fees(x["price"], x["quantity"]) for x in tr)
                execmsg = new_message(
                    message_type=MessageType.ORDER_EXECUTED,
                    sender_id="Exchange",
                    recipient_id=aid,
                    send_time=now,
                    recive_time=now,
                    content={
                        "trades": tr,
                        "stock": stock,
                        "fees": round(total_fee, 6),
                        "phase": "open_auction",
                    },
                )
                self._emit(execmsg)

            # Update OHLC open bar at 09:25 using clearing price if any trade
            sym = str(stock)
            self.ohlc_by_stock.setdefault(
                sym, OHLCAggregator(sym, self.ohlc_freq, self.logger)
            )
            if trades:
                vol = float(sum(t["quantity"] for t in trades))
                px = float(trades[0]["price"]) if trades else None
                if px is not None:
                    self.ohlc_by_stock[sym].update(now, px, volume=vol)
                    self._last_price[sym] = px

            # Carry remaining quantities into continuous book
            for o in remaining:
                lob_c = self._ensure_lob(stock)
                if lob_c is not None:
                    lob_c.add_order(o)
            self._auction_done[stock] = True

    # Note: preopen snapshot aggregation is provided by PreopenOrderBook.snapshot_top_n

    @staticmethod
    def _format_snapshot_csv_from_lists(asks: list, bids: list, n: int = 5) -> str:
        parts = []
        for i in range(n):
            parts.append(f"{asks[i][0]:.2f}" if i < len(asks) else "")
        for i in range(n):
            parts.append(str(asks[i][1]) if i < len(asks) else "")
        for i in range(n):
            parts.append(f"{bids[i][0]:.2f}" if i < len(bids) else "")
        for i in range(n):
            parts.append(str(bids[i][1]) if i < len(bids) else "")
        return ",".join(parts)

    def _tick_log(self, now: pd.Timestamp):
        # During pre-open window, log indicative book from preopen orders as LOB;
        # otherwise fall back to base behavior (continuous LOB snapshot)
        if self.opening_call and self.is_preopen_time(now):
            # Early auction if idle for > 3 seconds
            try:
                if self._preopen_last_order_ts is not None and (
                    now - self._preopen_last_order_ts
                ) >= pd.Timedelta(seconds=3):
                    self._run_call_auction(now)
                    return
            except Exception:
                pass
            stocks = set(self.lob_dict.keys()) | set(self._preopen_books.keys())
            for stock in stocks:
                self._log_preopen_stock(stock, now)
            return
        # default behavior
        super()._tick_log(now)

    def _log_preopen_stock(self, stock: str, now: pd.Timestamp):
        book = self._preopen_books.get(stock) or PreopenOrderBook(stock)
        snap = book.snapshot_top_n(n=self.lob_log_level)
        asks = snap.get("sell", [])
        bids = snap.get("buy", [])
        # Ensure non-crossing representation for display: drop bids >= best ask
        if asks:
            best_ask = float(asks[0][0])
            bids = [b for b in bids if float(b[0]) < best_ask]
        # indicative mid for OHLC
        if asks and bids and self.logger is not None:
            ap = float(asks[0][0])
            bp = float(bids[0][0])
            mid = round((ap + bp) / 2.0, 2)
            sym = str(stock)
            self.ohlc_by_stock.setdefault(
                sym, OHLCAggregator(sym, self.ohlc_freq, self.logger)
            )
            self.ohlc_by_stock[sym].update(now, mid, volume=0.0)
            self._last_price[sym] = mid
        # LOB periodic log control
        if self.logger is not None:
            sym = str(stock)
            csv = self._format_snapshot_csv_from_lists(
                asks, bids, n=self.lob_log_level
            )
            # write to preopen.csv instead of lob.csv
            self.logger.preopen_log(
                stock_name=sym,
                kernel_time=now,
                level=self.lob_log_level,
                lob=csv,
            )
            self._last_lob_log[sym] = now
        # Also honor subscriptions during pre-open using indicative book
        try:
            for aid, mp in list(self._subs.items()):
                sub = mp.get(stock)
                if not sub:
                    continue
                last = sub.get("last_sent")
                freq = int(sub.get("freq_ms", 1000))
                if last is None or (now - last) >= pd.Timedelta(milliseconds=freq):
                    depth = int(sub.get("depth", 1))
                    # limit lists to depth
                    pbids = bids[:depth]
                    pasks = asks[:depth]
                    msg = new_message(
                        message_type=MessageType.MKT_DATA,
                        sender_id="Exchange",
                        recipient_id=aid,
                        send_time=now,
                        recive_time=now,
                        content={
                            "stock": stock,
                            "depth": depth,
                            "bids": pbids,
                            "asks": pasks,
                            "ts": str(now),
                            "phase": "preopen",
                        },
                    )
                    self._emit(msg)
                    sub["last_sent"] = now
        except Exception:
            pass

    def _validate_order(self, order: Order, now: pd.Timestamp) -> bool:
        # Enforce price limits only for limit orders when reference available
        if isinstance(order, LimitOrder) and self.price_limit_pct > 0.0:
            ref = self._last_price.get(getattr(order, "_stock", ""))
            if ref and ref > 0:
                up = ref * (1.0 + self.price_limit_pct)
                dn = ref * (1.0 - self.price_limit_pct)
                if not (dn <= float(order.price) <= up):
                    return False
        # T+1: prevent selling shares bought today unless initial position covers
        if self.t_plus_one and getattr(order, "side", None) == "sell":
            if getattr(order, "_exempt_t1", False):
                return True
            agent = getattr(order, "agent_id", None)
            stock = getattr(order, "_stock", None) or getattr(order, "stock", None)
            if agent and stock:
                # If no initial_positions information, cannot infer prior-day holdings; do not block sells.
                if not self.initial_positions or agent not in self.initial_positions:
                    return True
                key = (agent, stock)
                init_pos = int(
                    ((self.initial_positions.get(agent) or {}).get(stock) or 0)
                )
                available = self._t1_available.get(key)
                if available is None:
                    available = init_pos
                    self._t1_available[key] = available
                if int(order.quantity) > max(0, available):
                    return False
                setattr(order, "_t1_reserved_qty", int(order.quantity))
        return True

    def _process_order(self, now: pd.Timestamp, order: Order):
        # Track day buys/sells for T+1
        side = getattr(order, "side", None)
        stock = getattr(order, "_stock", None) or getattr(order, "stock", None)
        agent = getattr(order, "agent_id", None)
        if side in ("buy", "sell") and stock and agent:
            key = (agent, stock)
            if side == "buy":
                self._day_buys[key] = int(self._day_buys.get(key, 0)) + int(
                    order.quantity
                )
            else:
                self._day_sells[key] = int(self._day_sells.get(key, 0)) + int(
                    order.quantity
                )
                qty = int(getattr(order, "_t1_reserved_qty", order.quantity))
                available = int(self._t1_available.get(key, 0))
                self._t1_available[key] = max(0, available - qty)
        super()._process_order(now, order)


class NYSEExchange(Exchange):
    """NYSE-like rules: no T+1, no price limits by default; fee structure configurable."""

    def __init__(self, *args, fee_rate: float = 0.0002, **kwargs):
        super().__init__(*args, **kwargs)
        self.fee_rate = float(fee_rate) if fee_rate else 0.0


def new_exchange(
    exchange_type: str,
    *,
    stocks: Iterable[str],
    logger=None,
    exchange_params: Optional[Dict] = None,
    out_queue=None,
):
    p = exchange_params or {}
    common = dict(
        stocks=stocks,
        logger=logger,
        ohlc_freq=p.get("ohlc_freq", "3s"),
        lob_log_level=p.get("lob_log_level", 5),
        lob_log_freq=p.get("lob_log_freq", "3s"),
        workers=int(p.get("workers", 0)),
        out_queue=out_queue,
        market_cap_range=p.get("market_cap_range"),
        trade_log_enabled=bool(p.get("trade_log_enabled", False)),
        trade_log_path=p.get("trade_log_path"),
        selector_update_freq=p.get("selector_update_freq", "60s"),
    )
    et = (exchange_type or "SZSE").upper()
    if et == "SZSE":
        return SZSExchange(
            **common,
            t_plus_one=bool(p.get("t_plus_one", True)),
            price_limit_pct=float(p.get("price_limit_pct", 0.1)),
            fee_rate=float(p.get("fee_rate", 0.0003)),
            initial_positions=p.get("initial_positions"),
            initial_snapshots=p.get("initial_snapshots"),
            opening_call=bool(p.get("opening_call", False)),
        )
    elif et == "NYSE":
        return NYSEExchange(
            **common,
            fee_rate=float(p.get("fee_rate", 0.0002)),
        )
    else:
        # Fallback to generic
        raise ValueError(f"Unknown exchange type: {exchange_type}")
