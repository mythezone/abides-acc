import pandas as pd
import numpy as np


from typing import List, TYPE_CHECKING, Optional, Dict, Tuple
from core.message import Message, MessageType, MessageQueue, new_message
from core.logger import Logger
from core.portfolio import Portfolio
from util.util import random_china_location, network_latency_ms


if TYPE_CHECKING:
    from core.kernel import Kernel


class BaseAgent:
    def __init__(
        self,
        id,
        *args,
        logger: Optional[Logger] | None = None,
        location: List[float] | Tuple[float, float] | None = None,
        message_queue: MessageQueue | None = None,
        **kwargs,
    ):
        self.id = id
        self.message_queue = message_queue or MessageQueue()
        self.inbox = []
        self.args = args
        self.current_time: pd.Timestamp = pd.Timestamp.now()
        self.logger = logger
        initial_cash = float(kwargs.pop("initial_cash", 1_000_000))
        self.agent_log_freq = kwargs.pop("agent_log_freq", "tick")
        try:
            self._agent_log_delta = (
                None
                if str(self.agent_log_freq).lower() == "tick"
                else pd.Timedelta(str(self.agent_log_freq))
            )
        except Exception:
            self._agent_log_delta = None
        self._agent_log_last: Optional[pd.Timestamp] = None
        self.portfolio = Portfolio(initial_cash=initial_cash)
        # Performance tracking options
        self.track_performance: bool = bool(kwargs.pop("track_performance", False))
        self._initial_nav: float = float(
            kwargs.pop("initial_nav", self.portfolio.current_total_value())
        )
        location_value = location if location is not None else kwargs.pop("location", None)
        if location_value is None:
            self.location: Tuple[float, float] = random_china_location()
        else:
            try:
                lat, lon = location_value
                self.location = (float(lat), float(lon))
            except Exception:
                self.location = random_china_location()
        self.exchange_location: Optional[Tuple[float, float]] = kwargs.pop(
            "exchange_location", None
        )
        self._peer_locations: Dict[str, Tuple[float, float]] = {}
        self._latest_symbol_response: Dict[str, object] | None = None
        # Calibration flags
        self.calibration_mode: bool = bool(kwargs.pop("calibration_mode", False))
        self.oracle_id: Optional[str] = kwargs.pop("oracle_id", None)

        for key, value in kwargs.items():
            setattr(self, key, value)

    def send(
        self,
        message: Message,
        delay: Optional[float] = None,
        *,
        delay_mode: str = "latency",
    ):
        # Align with MessageQueue.put(message, recive_delay=...)
        computed_delay = delay
        if delay is None and delay_mode == "latency":
            computed_delay = 0.0
            recipient = getattr(message, "recipient_id", None)
            if isinstance(recipient, str):
                if recipient == "Exchange" and self.exchange_location is not None:
                    computed_delay = network_latency_ms(self.location, self.exchange_location)
                else:
                    peer_loc = self._peer_locations.get(recipient)
                    if peer_loc is not None:
                        computed_delay = network_latency_ms(self.location, peer_loc)
        elif delay is None:
            computed_delay = 0.0
        if self.logger:
            # Log the sending event (stage=SEND)
            self.logger.kernel_message_log(message, stage="SEND")
        self.message_queue.put(message, recive_delay=computed_delay)

    def wakeup_delay(self):
        # Use slower cadence during pre-open call auction if configured
        preopen = False
        try:
            t = getattr(self, "current_time", None)
            if t is not None:
                to = pd.to_datetime(t).time()
                preopen = (
                    pd.Timestamp("09:15").time() <= to < pd.Timestamp("09:25").time()
                )
        except Exception:
            preopen = False
        rng = None
        if preopen:
            rng = getattr(self, "auction_wakeup_ms_range", None)
        if rng is None:
            rng = getattr(self, "wakeup_ms_range", None)
        if rng and isinstance(rng, (list, tuple)) and len(rng) == 2:
            lo, hi = int(rng[0]), int(rng[1])
            hi = max(hi, lo + 1)
            return int(np.random.randint(lo, hi))
        return int(np.random.randint(1000, 5000))

    def set_next_wakeup(self, current_time, intelver: int = -1):
        if intelver < 0:
            intelver = self.wakeup_delay()

        wakeup_time = current_time + pd.Timedelta(milliseconds=intelver)
        msg = new_message(
            message_type=MessageType.WAKEUP,
            sender_id=self.id,
            recipient_id=self.id,
            send_time=current_time,
            recive_time=wakeup_time,
            content={},
        )
        self.send(msg)

    def process_inbox(self):
        # default handler: update portfolio on executions
        for m in self.inbox:
            if m.message_type == MessageType.ORDER_EXECUTED and isinstance(
                m.content, dict
            ):
                trades = m.content.get("trades", [])
                for t in trades:
                    symbol = t.get("symbol")
                    price = float(t.get("price", 0.0))
                    qty = int(t.get("quantity", 0))
                    # Determine if this agent is buyer or seller in this trade
                    if t.get("buy") == self.id:
                        self.portfolio.apply_trade(symbol, "buy", price, qty)
                    if t.get("sell") == self.id:
                        self.portfolio.apply_trade(symbol, "sell", price, qty)
                # Deduct fees if provided
                try:
                    fees = float(m.content.get("fees", 0.0))
                    if fees > 0:
                        self.portfolio.cash -= fees
                except Exception:
                    pass
            elif m.message_type == MessageType.SELECT_SYMBOLS_RESPONSE and isinstance(m.content, dict):
                self._latest_symbol_response = m.content
            else:
                self.handle_inbox_message(m)
        self.inbox = []

    def action(self):
        pass

    def request_oracle(self, symbol: str, kind: str = "lob"):
        if not self.calibration_mode or not self.oracle_id:
            return
        mtype = (
            MessageType.ORACLE_QUERY_LOB
            if kind == "lob"
            else MessageType.ORACLE_QUERY_OHLC
        )
        msg = new_message(
            message_type=mtype,
            sender_id=self.id,
            recipient_id=self.oracle_id,
            send_time=self.current_time,
            recive_time=self.current_time,
            content={"symbol": symbol, "time": str(self.current_time)},
        )
        self.send(msg)

    def wakeup(self, current_time):
        self.current_time = current_time
        self.set_next_wakeup(current_time)
        self.process_inbox()
        self.action()
        if self.track_performance:
            self.log_performance(current_time)
        return

    def receive(self, message: Message):
        self.inbox.append(message)

    def handle_inbox_message(self, message: Message) -> bool:
        return False

    # --- Performance tracking helpers ---

    def current_total_value(self, price_map: Optional[dict] = None) -> float:
        return float(self.portfolio.current_total_value(price_map))

    def get_profit(self, price_map: Optional[dict] = None) -> float:
        return float(self.current_total_value(price_map) - self._initial_nav)

    def performance_snapshot(self, price_map: Optional[dict] = None) -> dict:
        total_val = self.current_total_value(price_map)
        return {
            "cash": round(float(self.portfolio.cash), 2),
            "total_value": round(total_val, 2),
            "profit": round(total_val - self._initial_nav, 2),
            "positions": dict(self.portfolio.holdings),
        }

    def log_performance(
        self,
        timestamp: Optional[pd.Timestamp] = None,
        price_map: Optional[dict] = None,
    ) -> None:
        if not (self.logger and self.track_performance):
            return
        ts = timestamp or self.current_time
        snapshot = self.performance_snapshot(price_map)
        self.logger.agent_log(
            agent_id=self.id,
            kernel_time=ts,
            cash=snapshot["cash"],
            total_value=snapshot["total_value"],
            positions=snapshot["positions"],
        )
        self._agent_log_last = ts

    # --- Exchange query helpers ---
    def build_fundamental_query(
        self,
        symbols: List[str],
        *,
        send_time: Optional[pd.Timestamp] = None,
    ) -> Optional[Message]:
        """Create a fundamental data request for one or more symbols.

        Returns a message targeting the exchange or ``None`` if no valid symbols
        were provided. Agents should add the resulting message to their outgoing
        list (alongside orders, etc.) before invoking ``send``.
        """

        if not symbols:
            return None
        valid_symbols = [str(sym) for sym in symbols if isinstance(sym, str)]
        if not valid_symbols:
            return None
        ts = send_time or self.current_time
        content = {"requests": [{"symbol": sym} for sym in valid_symbols]}
        return new_message(
            message_type=MessageType.QUERY_FUNDAMENTAL,
            sender_id=self.id,
            recipient_id="Exchange",
            send_time=ts,
            recive_time=ts,
            content=content,
        )

    def build_top_of_book_query(
        self,
        symbols: List[str],
        *,
        depth: int = 1,
        send_time: Optional[pd.Timestamp] = None,
    ) -> Optional[Message]:
        """Create a top-of-book snapshot request for the provided symbols."""

        if not symbols:
            return None
        valid_symbols = [str(sym) for sym in symbols if isinstance(sym, str)]
        if not valid_symbols:
            return None
        depth = max(1, int(depth))
        ts = send_time or self.current_time
        content = {
            "requests": [{"symbol": sym, "depth": depth} for sym in valid_symbols]
        }
        return new_message(
            message_type=MessageType.QUERY_TOP_OF_BOOK,
            sender_id=self.id,
            recipient_id="Exchange",
            send_time=ts,
            recive_time=ts,
            content=content,
        )

    def build_symbol_query(
        self,
        *,
        strategy: str = "random",
        count: int = 1,
        send_time: Optional[pd.Timestamp] = None,
        **params,
    ) -> Message:
        ts = send_time or self.current_time
        payload = {"strategy": str(strategy), "count": int(max(1, count))}
        if params:
            payload.update(params)
        return new_message(
            message_type=MessageType.SELECT_SYMBOLS_REQUEST,
            sender_id=self.id,
            recipient_id="Exchange",
            send_time=ts,
            recive_time=ts,
            content=payload,
        )

    def request_symbols(
        self,
        *,
        strategy: str = "random",
        count: int = 1,
        send_time: Optional[pd.Timestamp] = None,
        **params,
    ) -> None:
        msg = self.build_symbol_query(
            strategy=strategy,
            count=count,
            send_time=send_time,
            **params,
        )
        self.send(msg)
