from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Union, Dict

import pandas as pd

try:
    from tqdm import tqdm
except ImportError:  # pragma: no cover
    tqdm = None

from core.agent.base import BaseAgent
from core.message import MessageType, new_message


@dataclass
class _HistoricalOrder:
    time: pd.Timestamp
    side: str
    quantity: int
    price: Optional[float]
    order_id: Optional[str]
    is_market: bool
    market_depth: Optional[int]


@dataclass
class _HistoricalCancel:
    time: pd.Timestamp
    order_id: str
    quantity: Optional[int]


class HistoricalOrderReplayAgent(BaseAgent):
    """Replay historical order records as agent messages."""

    def __init__(
        self,
        id: str,
        *args,
        orders_csv: str,
        stock: str,
        start_time: Optional[str] = None,
        log_tick_after: bool = True,
        **kwargs,
    ):
        super().__init__(id, *args, **kwargs)
        self.stock = str(stock)
        self._log_tick_after = bool(log_tick_after)
        self._events: List[Union[_HistoricalOrder, _HistoricalCancel]] = []
        self._cursor = 0
        self._known_order_qty: Dict[str, int] = {}
        csv_path = Path(orders_csv)
        if not csv_path.exists():
            raise FileNotFoundError(f"Historical orders file not found: {orders_csv}")
        df = pd.read_csv(csv_path)
        if df.empty:
            raise ValueError(f"Historical orders file is empty: {orders_csv}")

        if start_time:
            base_time = pd.Timestamp(start_time)
        else:
            base_time = pd.to_datetime(df.iloc[0]["TIMESTAMP"])
        has_simutime = "SIMUTIME" in df.columns

        for row in df.to_dict("records"):
            sim_offset = float(row.get("SIMUTIME", 0.0)) if has_simutime else 0.0
            event_time = base_time + pd.to_timedelta(sim_offset, unit="s")
            if not has_simutime:
                try:
                    event_time = pd.to_datetime(row.get("TIMESTAMP", base_time))
                except Exception:
                    event_time = base_time

            side_flag = row.get("BUY_SELL_FLAG")
            if side_flag in (1, "1"):
                side = "buy"
            elif side_flag in (2, "2"):
                side = "sell"
            else:
                continue

            quantity = row.get("SIZE")
            if pd.isna(quantity):
                continue
            qty = int(quantity)
            if qty <= 0:
                continue

            order_type_val = row.get("ORDER_TYPE", "")
            order_type = str(order_type_val).strip()
            is_market = order_type == "1"

            cancel_type_val = row.get("CANCEL_TYPE")
            try:
                cancel_type = int(cancel_type_val)
            except Exception:
                cancel_type = None

            order_id_val = row.get("ORDER_ID")
            order_id = str(order_id_val) if pd.notna(order_id_val) else None

            if cancel_type == 2:
                if order_id is None:
                    continue
                cancel_qty: Optional[int] = qty if qty > 0 else None
                if order_id in self._known_order_qty:
                    if cancel_qty is None:
                        self._known_order_qty.pop(order_id, None)
                    else:
                        available = self._known_order_qty[order_id]
                        cancel_qty = min(cancel_qty, available)
                        remaining = available - cancel_qty
                        if remaining > 0:
                            self._known_order_qty[order_id] = remaining
                        else:
                            self._known_order_qty.pop(order_id, None)
                self._events.append(
                    _HistoricalCancel(
                        time=event_time,
                        order_id=order_id,
                        quantity=cancel_qty,
                    )
                )
                continue

            price_val = row.get("PRICE")

            price = None
            if not is_market and pd.notna(price_val):
                price = float(price_val)
            if not is_market and price is None:
                continue

            market_depth = row.get("MARKET_ORDER_TYPE")
            if pd.isna(market_depth):
                market_depth = None
            else:
                try:
                    market_depth = int(market_depth)
                except Exception:
                    market_depth = None

            order_event = _HistoricalOrder(
                time=event_time,
                side=side,
                quantity=qty,
                price=price,
                order_id=order_id,
                is_market=is_market,
                market_depth=market_depth,
            )
            self._events.append(order_event)

            if not order_event.is_market and order_event.order_id is not None:
                self._known_order_qty[order_event.order_id] = int(order_event.quantity)

        self._events.sort(key=lambda item: item.time)
        self._time_epsilon = pd.Timedelta(microseconds=100)
        self._scheduled_time: Optional[pd.Timestamp] = None
        self._progress = (
            tqdm(total=len(self._events), desc=f"{self.id} replay", unit="event")
            if tqdm is not None
            else None
        )
        if not self._events and self._progress is not None:
            self._progress.close()
            self._progress = None

    def wakeup(self, current_time):
        self.current_time = current_time
        self.process_inbox()
        self._scheduled_time = None
        self._emit_orders_until(current_time)
        if self._cursor >= len(self._events):
            self._finalize_progress()
        else:
            self._schedule_next_event()

    def _emit_orders_until(self, current_time: pd.Timestamp) -> None:
        while self._cursor < len(self._events):
            event = self._events[self._cursor]
            if event.time - current_time > self._time_epsilon:
                break
            if isinstance(event, _HistoricalOrder):
                self._send_submit(event)
            else:
                self._send_cancel(event)
            self._cursor += 1
            if self._progress is not None:
                self._progress.update(1)
                self._progress.set_postfix(
                    {
                        "current_time": str(event.time),
                        "remaining": len(self._events) - self._cursor,
                    },
                    refresh=False,
                )

    def _send_submit(self, order: _HistoricalOrder) -> None:
        req: dict = {
            "type": "market_order" if order.is_market else "limit_order",
            "stock": self.stock,
            "agent_id": self.id,
            "timestamp": str(order.time),
            "side": order.side,
            "quantity": int(order.quantity),
        }
        if not order.is_market and order.price is not None:
            req["price"] = float(order.price)
        if order.order_id is not None:
            req["id"] = order.order_id
        if order.is_market and order.market_depth is not None:
            req["market_depth"] = order.market_depth
        msg = new_message(
            message_type=MessageType.SUBMIT_ORDER,
            sender_id=self.id,
            recipient_id="Exchange",
            send_time=order.time,
            recive_time=order.time,
            content={"requests": [req]},
        )
        self.send(msg)

    def _send_cancel(self, cancel: _HistoricalCancel) -> None:
        req = {
            "stock": self.stock,
            "order_id": cancel.order_id,
        }
        if cancel.quantity is not None:
            req["quantity"] = int(cancel.quantity)
        msg = new_message(
            message_type=MessageType.CANCEL_ORDER,
            sender_id=self.id,
            recipient_id="Exchange",
            send_time=cancel.time,
            recive_time=cancel.time,
            content={"requests": [req]},
        )
        self.send(msg)

    def _next_order_time(self) -> Optional[pd.Timestamp]:
        if self._cursor < len(self._events):
            return self._events[self._cursor].time
        return None

    def _schedule_next_event(self) -> None:
        next_time = self._next_order_time()
        if next_time is None:
            return
        if self._scheduled_time is not None:
            delta = (next_time - self._scheduled_time).abs()
            if delta <= self._time_epsilon:
                return
        self._scheduled_time = next_time
        self.schedule_message(
            when=next_time,
            message_type=MessageType.WAKEUP,
            recipient_id=self.id,
            content={},
            sender_id=self.id,
        )

    def _finalize_progress(self) -> None:
        if self._progress is not None:
            self._progress.close()
            self._progress = None
