import numpy as np
import pandas as pd
from typing import List, Optional

from core.agent.base import BaseAgent
from core.message import MessageType, new_message


class ValueAgent(BaseAgent):
    """
    ABIDES-style ValueAgent adapter.

    - If calibration/oracle is enabled, queries OHLC for a symbol and places orders near last close.
    - Otherwise falls back to simple limit orders around a random reference.
    """

    def __init__(
        self,
        id: str,
        *args,
        initial_symbols: Optional[List[str]] = None,
        **kwargs,
    ):
        super().__init__(id, *args, **kwargs)
        self.subscribed_symbols: List[str] = (initial_symbols or [])[:]

    def action(self):
        if not self.subscribed_symbols:
            return
        sym = str(np.random.choice(self.subscribed_symbols))
        # If oracle available, request OHLC snapshot first; we will act in receive()
        if getattr(self, "calibration_mode", False) and self.oracle_id:
            msg = new_message(
                message_type=MessageType.ORACLE_QUERY_OHLC,
                sender_id=self.id,
                recipient_id=self.oracle_id,
                send_time=self.current_time,
                recive_time=self.current_time,
                content={"symbol": sym, "time": str(self.current_time)},
            )
            self.send(msg)
            return
        # Fallback: place simple buy/sell around synthetic ref
        ref = float(np.random.uniform(20, 80))
        self._emit_orders_near(sym, ref)

    def handle_inbox_message(self, message):
        if (
            message.message_type == MessageType.ORACLE_RESPONSE_OHLC
            and isinstance(message.content, dict)
        ):
            sym = str(message.content.get("symbol"))
            data = message.content.get("ohlc") or {}
            try:
                close = data.get("close")
                if close is not None and close != "":
                    self._emit_orders_near(sym, float(close))
            except Exception:
                pass
            return True
        return super().handle_inbox_message(message)

    def _emit_orders_near(self, symbol: str, ref: float):
        # one buy, one sell (sell only if inventory)
        reqs = []
        buy_px = round(max(0.01, ref * (1.0 - 0.002)), 2)
        reqs.append(
            {
                "type": "limit_order",
                "symbol": symbol,
                "agent_id": self.id,
                "timestamp": str(self.current_time),
                "side": "buy",
                "quantity": int(np.random.randint(1, 50)),
                "price": buy_px,
            }
        )
        inv = int(self.portfolio.holdings.get(symbol, 0))
        if inv > 0:
            qty = max(1, min(int(np.random.randint(1, 50)), inv))
            sell_px = round(ref * (1.0 + 0.002), 2)
            reqs.append(
                {
                    "type": "limit_order",
                    "symbol": symbol,
                    "agent_id": self.id,
                    "timestamp": str(self.current_time),
                    "side": "sell",
                    "quantity": qty,
                    "price": sell_px,
                }
            )
        msg = new_message(
            message_type=MessageType.SUBMIT_ORDER,
            sender_id=self.id,
            recipient_id="Exchange",
            send_time=self.current_time,
            recive_time=self.current_time,
            content={"requests": reqs},
        )
        self.send(msg)
