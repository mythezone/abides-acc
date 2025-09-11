from core.lob import LimitOrderBook
from core.message import MessageType, new_message, Message
from core.ohlc import OHLCAggregator
from core.order import Order, LimitOrder, MarketOrder
import pandas as pd
import numpy as np


import threading
from queue import Queue
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Dict, Tuple
from core.preopen_book import PreopenOrderBook
from core.logger import Logger


class Exchange:
    """Generic exchange with basic LOB, OHLC logging and optional workers.

    Subclasses may override validation and fee rules.
    """

    def __init__(
        self,
        symbols: dict,
        logger: Logger,
        ohlc_freq: str = "3s",
        lob_log_level: int = 5,
        lob_log_freq: str = "3s",
        workers: int = 0,
        out_queue=None,
        **kwargs,
    ):
        self.symbols = symbols
        self.lob_dict = {
            symbol_name: LimitOrderBook(symbol_name) for symbol_name in symbols
        }
        self.logger = logger
        self.ohlc_freq = ohlc_freq
        self.ohlc_by_symbol: dict[str, OHLCAggregator] = {}
        self.lob_log_level = lob_log_level
        # support special tick mode
        self._lob_tick_mode = str(lob_log_freq).lower() == "tick"
        self.lob_log_delta = None if self._lob_tick_mode else pd.Timedelta(lob_log_freq)
        self._last_lob_log: dict[str, pd.Timestamp] = {}
        self.out_queue = out_queue
        self.is_open: bool = True
        # Price references and last prices per symbol for limit checks in subclasses
        self._last_price: Dict[str, float] = {}
        # Fee rate in bps (subclasses may override)
        self.fee_rate: float = 0.0  # e.g., 0.0003 = 3 bps
        # Optional initial positions for account-aware rules (agent_id -> {symbol: qty})
        self.initial_positions: Dict[str, Dict[str, int]] = {}
        # Per-day buy/sell counters for T+1 enforcement
        self._day_buys: Dict[Tuple[str, str], int] = {}  # (agent,symbol)->qty
        self._day_sells: Dict[Tuple[str, str], int] = {}

        # Parallel workers sharded by symbol hash (if requested)
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
        for key, value in kwargs.items():
            setattr(self, key, value)

    def handle_message(self, message: Message):
        response_messages = []
        now = message.send_time
        # PROC log for incoming message at Exchange
        if self.logger is not None:
            self.logger.kernel_message_log(message, stage="PROC")

        if message.message_type in (
            MessageType.LMT_ORDER,
            MessageType.MKT_ORDER,
            MessageType.SUBMIT_ORDER,
        ):
            # Accept generic SUBMIT_ORDER and type-specific LMT/MKT
            for req in message.content.get("requests", []):
                symbol = req.get("symbol", "SYM")
                # Ensure a LOB exists even if symbols were not pre-registered
                if symbol not in self.lob_dict:
                    self.lob_dict[symbol] = LimitOrderBook(symbol)

                # Decide order class
                otype = req.get("type")
                if otype == "limit_order":
                    order = LimitOrder.from_dict(req)
                elif otype == "market_order":
                    order = MarketOrder.from_dict(req)
                else:
                    order = Order.from_dict(req)

                # attach symbol reference and flags to order for worker processing
                try:
                    setattr(order, "_symbol", symbol)
                    # BG agents are exempt from T+1
                    sender_lower = str(message.sender_id).lower()
                    if sender_lower.startswith("background_"):
                        setattr(order, "_exempt_t1", True)
                except Exception:
                    pass
                if self._validate_order(order, now):
                    # Allow subclasses to intercept pre-open routing
                    if self._route_preopen(order, now):
                        continue
                    if self.workers > 0:
                        # Enqueue to worker based on symbol shard
                        shard = hash(symbol) % self.workers
                        self._worker_queues[shard].put((now, order))
                    else:
                        # Synchronous processing
                        self._process_order(now, order)
                else:
                    # Reject order outside rules silently (could emit rejection message)
                    pass
        elif message.message_type == MessageType.CANCEL_ORDER:
            for req in message.content.get("requests", []):
                symbol = req.get("symbol")
                order_id = req.get("order_id")
                self.lob_dict[symbol].cancel_order(order_id)
                response_messages.append(
                    new_message(
                        message_type=MessageType.ORDER_CANCELLED,
                        sender_id="Exchange",
                        recipient_id=message.sender_id,
                        send_time=now,
                        recive_time=now,
                        content={"order_id": order_id, "symbol": symbol},
                    )
                )
        elif message.message_type in (MessageType.MKT_OPEN, MessageType.MKT_CLOSE):
            # Toggle trading session state; primarily informational for now
            self.is_open = message.message_type == MessageType.MKT_OPEN
            if self.logger is not None:
                self.logger.exchange_log(
                    f"Market {'OPEN' if self.is_open else 'CLOSE'}",
                    kernel_time=now,
                    type_="SESSION",
                )
        elif message.message_type == MessageType.MKT_DATA:
            content = message.content or {}
            if content.get("type") == "query_symbols":
                n = int(content.get("n", 3))
                # Provide dummy symbol list
                universe = list(self.lob_dict.keys()) or [
                    "SYM1",
                    "SYM2",
                    "SYM3",
                    "SYM4",
                ]
                if len(universe) < n:
                    # Pad with synthetic symbols
                    universe += [f"SYM{i}" for i in range(len(universe) + 1, n + 1)]
                selected = universe[:n]
                response_messages.append(
                    new_message(
                        message_type=MessageType.MKT_DATA,
                        sender_id="Exchange",
                        recipient_id=message.sender_id,
                        send_time=now,
                        recive_time=now,
                        content={"symbols": selected},
                    )
                )
            else:
                for req in content.get("requests", []):
                    symbol = req.get("symbol", "SYM1")
                    # Return a dummy snapshot
                    best_bid = round(np.random.uniform(10, 100), 2)
                    best_ask = round(best_bid + np.random.uniform(0.01, 0.5), 2)
                    snapshot = {
                        "symbol": symbol,
                        "best_bid": best_bid,
                        "best_ask": best_ask,
                        "mid": round((best_bid + best_ask) / 2, 2),
                        "ts": str(now),
                    }
                    response_messages.append(
                        new_message(
                            message_type=MessageType.MKT_DATA,
                            sender_id="Exchange",
                            recipient_id=message.sender_id,
                            send_time=now,
                            recive_time=now,
                            content=snapshot,
                        )
                    )
        elif message.message_type == MessageType.LOG_TICK:
            # Heartbeat to emit periodic logs even without orders
            try:
                self._tick_log(now)
            except Exception:
                pass
        return response_messages

    def _tick_log(self, now: pd.Timestamp):
        # For each symbol, emit OHLC and periodic LOB snapshot per configured frequency
        for symbol, lob in self.lob_dict.items():
            # Determine a working price: prefer last trade via aggregator, else mid from book
            price = None
            snap = lob.snapshot_top_n(1)
            if snap["buy"] and snap["sell"]:
                bid = float(snap["buy"][0][0])
                ask = float(snap["sell"][0][0])
                price = round((bid + ask) / 2.0, 2)
            if price is not None and self.logger is not None:
                if symbol not in self.ohlc_by_symbol:
                    self.ohlc_by_symbol[symbol] = OHLCAggregator(
                        symbol, self.ohlc_freq, self.logger
                    )
                self.ohlc_by_symbol[symbol].update(now, price, volume=0.0)
                self._last_price[symbol] = float(price)
            # LOB periodic log check
            if self.logger is not None:
                last = self._last_lob_log.get(symbol)
                should_log = False
                if self._lob_tick_mode:
                    should_log = True
                else:
                    if (last is None) or (now - last >= self.lob_log_delta):
                        should_log = True
                if should_log:
                    level = self.lob_log_level
                    lob_csv = lob.format_snapshot_csv(level)
                    self.logger.lob_log(
                        symbol_name=symbol, kernel_time=now, level=level, lob=lob_csv
                    )
                    self._last_lob_log[symbol] = now

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
        if self.out_queue is not None:
            self.out_queue.put(msg)

    def _process_order(self, now: pd.Timestamp, order: Order):
        symbol = (
            getattr(order, "_symbol", None) or getattr(order, "symbol", None) or None
        )
        if symbol is None:
            # fallback from request dict stored in order
            if hasattr(order, "__dict__") and "symbol" in order.__dict__:
                symbol = order.__dict__["symbol"]
        if symbol not in self.lob_dict:
            self.lob_dict[symbol] = LimitOrderBook(symbol)

        trades = self.lob_dict[symbol].add_order(order)
        # Acknowledge
        ack = new_message(
            message_type=MessageType.ORDER_ACCEPTED,
            sender_id="Exchange",
            recipient_id=order.agent_id,
            send_time=now,
            recive_time=now,
            content={"order_id": order.id, "symbol": symbol},
        )
        self._emit(ack)

        if trades:
            # accumulate fee
            total_fee = 0.0
            for t in trades:
                # track last price
                try:
                    self._last_price[symbol] = float(t["price"])  # per our trade dict
                except Exception:
                    pass
                total_fee += self._apply_fees(t.get("price", 0.0), t.get("quantity", 0))
            execmsg = new_message(
                message_type=MessageType.ORDER_EXECUTED,
                sender_id="Exchange",
                recipient_id=order.agent_id,
                send_time=now,
                recive_time=now,
                content={
                    "trades": trades,
                    "symbol": symbol,
                    "fees": round(total_fee, 6),
                },
            )
            self._emit(execmsg)

        # OHLC update
        price = None
        if trades:
            price = float(trades[-1]["price"])
        else:
            snap = self.lob_dict[symbol].snapshot_top_n(1)
            if snap["buy"] and snap["sell"]:
                bid = float(snap["buy"][0][0])
                ask = float(snap["sell"][0][0])
                price = round((bid + ask) / 2.0, 2)
        if price is not None and self.logger is not None:
            if symbol not in self.ohlc_by_symbol:
                self.ohlc_by_symbol[symbol] = OHLCAggregator(
                    symbol, self.ohlc_freq, self.logger
                )
            self.ohlc_by_symbol[symbol].update(now, price, volume=float(order.quantity))
            self._last_price[symbol] = float(price)
        # LOB periodic log
        if self.logger is not None:
            last = self._last_lob_log.get(symbol)
            should_log = False
            if self._lob_tick_mode:
                should_log = True
            else:
                if (last is None) or (now - last >= self.lob_log_delta):
                    should_log = True
            if should_log:
                lob_csv = self.lob_dict[symbol].format_snapshot_csv(self.lob_log_level)
                self.logger.lob_log(
                    symbol_name=symbol,
                    kernel_time=now,
                    level=self.lob_log_level,
                    lob=lob_csv,
                )
                self._last_lob_log[symbol] = now

    def shutdown(self, wait: bool = True):
        """Gracefully stop background workers and flush aggregators/logs.

        This prevents lingering non-daemon threads from keeping the process alive
        after simulations complete.
        """
        # Flush OHLC aggregators
        try:
            for agg in self.ohlc_by_symbol.values():
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


class SZSExchange(Exchange):
    """SZSE-like rules: optional T+1, price limits, and fees on executions."""

    def __init__(
        self,
        *args,
        t_plus_one: bool = True,
        price_limit_pct: float = 0.1,
        fee_rate: float = 0.0003,
        initial_positions: Optional[Dict[str, Dict[str, int]]] = None,
        opening_call: bool = False,
        **kwargs,
    ):
        # opening_call is handled here and not passed to base class
        super().__init__(*args, **kwargs)
        self.t_plus_one = bool(t_plus_one)
        self.price_limit_pct = float(price_limit_pct) if price_limit_pct else 0.0
        self.fee_rate = float(fee_rate) if fee_rate else 0.0
        self.initial_positions = initial_positions or {}
        # opening call auction placeholders (not fully implemented)
        self.opening_call = bool(opening_call)
        # Pre-open call auction storage
        self._preopen_books: Dict[str, PreopenOrderBook] = {}
        self._auction_done: Dict[str, bool] = {}
        self._preopen_once: set[tuple[str, str]] = set()  # (agent_id, symbol)
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
        symbol = getattr(order, "_symbol", None) or getattr(order, "symbol", None)
        if symbol is None:
            return False
        key = (getattr(order, "agent_id", ""), symbol)
        # Allow only one submission per agent per symbol during pre-open
        if key in self._preopen_once:
            return True
        self._preopen_once.add(key)
        book = self._preopen_books.setdefault(symbol, PreopenOrderBook(symbol))
        book.add_order(order)
        self._preopen_last_order_ts = now
        # ACK acceptance
        ack = new_message(
            message_type=MessageType.ORDER_ACCEPTED,
            sender_id="Exchange",
            recipient_id=order.agent_id,
            send_time=now,
            recive_time=now,
            content={"order_id": order.id, "symbol": symbol, "phase": "preopen"},
        )
        self._emit(ack)
        # Opportunistic preopen snapshot log for this symbol
        try:
            self._log_preopen_symbol(symbol, now)
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
        # For each symbol, if auction not done and there are preopen orders, determine opening price and match
        for symbol, book in list(self._preopen_books.items()):
            if self._auction_done.get(symbol, False):
                continue
            snap = book.snapshot_top_n(1)
            # If no book content, mark done
            if not (snap.get("buy") or snap.get("sell")):
                self._auction_done[symbol] = True
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
                        "symbol": symbol,
                        "fees": round(total_fee, 6),
                        "phase": "open_auction",
                    },
                )
                self._emit(execmsg)

            # Update OHLC open bar at 09:25 using clearing price if any trade
            self.ohlc_by_symbol.setdefault(
                symbol, OHLCAggregator(symbol, self.ohlc_freq, self.logger)
            )
            if trades:
                vol = float(sum(t["quantity"] for t in trades))
                px = float(trades[0]["price"]) if trades else None
                if px is not None:
                    self.ohlc_by_symbol[symbol].update(now, px, volume=vol)
                    self._last_price[symbol] = px

            # Carry remaining quantities into continuous book
            for o in remaining:
                self.lob_dict.setdefault(symbol, LimitOrderBook(symbol))
                self.lob_dict[symbol].add_order(o)
            self._auction_done[symbol] = True

    def _preopen_snapshot_top_n(self, symbol: str, n: int = 5):
        orders = [o for o in self._preopen_orders.get(symbol, []) if o is not None]
        bids: Dict[float, int] = {}
        asks: Dict[float, int] = {}
        for o in orders:
            price = getattr(o, "price", None)
            if price is None:
                # market orders do not contribute to top-of-book price levels
                continue
            p = float(price)
            if getattr(o, "side", None) == "buy":
                bids[p] = int(bids.get(p, 0)) + int(o.quantity)
            elif getattr(o, "side", None) == "sell":
                asks[p] = int(asks.get(p, 0)) + int(o.quantity)
        # sort: bids desc, asks asc
        bid_lvls = sorted(bids.items(), key=lambda x: -x[0])[:n]
        ask_lvls = sorted(asks.items(), key=lambda x: x[0])[:n]
        return {"buy": bid_lvls, "sell": ask_lvls}

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
            symbols = set(self.lob_dict.keys()) | set(self._preopen_books.keys())
            for symbol in symbols:
                self._log_preopen_symbol(symbol, now)
            return
        # default behavior
        super()._tick_log(now)

    def _log_preopen_symbol(self, symbol: str, now: pd.Timestamp):
        book = self._preopen_books.get(symbol) or PreopenOrderBook(symbol)
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
            self.ohlc_by_symbol.setdefault(
                symbol, OHLCAggregator(symbol, self.ohlc_freq, self.logger)
            )
            self.ohlc_by_symbol[symbol].update(now, mid, volume=0.0)
            self._last_price[symbol] = mid
        # LOB periodic log control
        if self.logger is not None:
            last = self._last_lob_log.get(symbol)
            should_log = False
            if self._lob_tick_mode:
                should_log = True
            else:
                if (last is None) or (now - last >= self.lob_log_delta):
                    should_log = True
            if should_log:
                csv = self._format_snapshot_csv_from_lists(
                    asks, bids, n=self.lob_log_level
                )
                # write to preopen.csv instead of lob.csv
                self.logger.preopen_log(
                    symbol_name=symbol,
                    kernel_time=now,
                    level=self.lob_log_level,
                    lob=csv,
                )
                self._last_lob_log[symbol] = now

    def _validate_order(self, order: Order, now: pd.Timestamp) -> bool:
        # Enforce price limits only for limit orders when reference available
        if isinstance(order, LimitOrder) and self.price_limit_pct > 0.0:
            ref = self._last_price.get(getattr(order, "_symbol", None))
            if ref is not None and ref > 0:
                up = ref * (1.0 + self.price_limit_pct)
                dn = ref * (1.0 - self.price_limit_pct)
                if not (dn <= float(order.price) <= up):
                    return False
        # T+1: prevent selling shares bought today unless initial position covers
        if self.t_plus_one and getattr(order, "side", None) == "sell":
            if getattr(order, "_exempt_t1", False):
                return True
            agent = getattr(order, "agent_id", None)
            symbol = getattr(order, "_symbol", None) or getattr(order, "symbol", None)
            if agent and symbol:
                # If no initial_positions information, cannot infer prior-day holdings; do not block sells.
                if not self.initial_positions or agent not in self.initial_positions:
                    return True
                key = (agent, symbol)
                buys = int(self._day_buys.get(key, 0))
                sells = int(self._day_sells.get(key, 0))
                init_pos = int(
                    ((self.initial_positions.get(agent) or {}).get(symbol) or 0)
                )
                # Max sellable today = init_pos - sells (cannot use today's buys)
                remaining = init_pos - sells
                if int(order.quantity) > max(0, remaining):
                    return False
        return True

    def _process_order(self, now: pd.Timestamp, order: Order):
        # Track day buys/sells for T+1
        side = getattr(order, "side", None)
        symbol = getattr(order, "_symbol", None) or getattr(order, "symbol", None)
        agent = getattr(order, "agent_id", None)
        if side in ("buy", "sell") and symbol and agent:
            key = (agent, symbol)
            if side == "buy":
                self._day_buys[key] = int(self._day_buys.get(key, 0)) + int(
                    order.quantity
                )
            else:
                self._day_sells[key] = int(self._day_sells.get(key, 0)) + int(
                    order.quantity
                )
        super()._process_order(now, order)


class NYSEExchange(Exchange):
    """NYSE-like rules: no T+1, no price limits by default; fee structure configurable."""

    def __init__(self, *args, fee_rate: float = 0.0002, **kwargs):
        super().__init__(*args, **kwargs)
        self.fee_rate = float(fee_rate) if fee_rate else 0.0


def new_exchange(
    exchange_type: str,
    *,
    symbols: dict,
    logger=None,
    exchange_params: Optional[Dict] = None,
    out_queue=None,
):
    p = exchange_params or {}
    common = dict(
        symbols=symbols,
        logger=logger,
        ohlc_freq=p.get("ohlc_freq", "3s"),
        lob_log_level=p.get("lob_log_level", 5),
        lob_log_freq=p.get("lob_log_freq", "3s"),
        workers=int(p.get("workers", 0)),
        out_queue=out_queue,
    )
    et = (exchange_type or "SZSE").upper()
    if et == "SZSE":
        return SZSExchange(
            **common,
            t_plus_one=bool(p.get("t_plus_one", True)),
            price_limit_pct=float(p.get("price_limit_pct", 0.1)),
            fee_rate=float(p.get("fee_rate", 0.0003)),
            initial_positions=p.get("initial_positions"),
            opening_call=bool(p.get("opening_call", False)),
        )
    elif et == "NYSE":
        return NYSEExchange(
            **common,
            fee_rate=float(p.get("fee_rate", 0.0002)),
        )
    else:
        # Fallback to generic
        return Exchange(**common)
