import numpy as np
from typing import List, Optional

from core.agent.base import BaseAgent
from core.message import MessageType, new_message


class FundamentalTrackingAgent(BaseAgent):
    """
    ABIDES-style FundamentalTrackingAgent adapter.

    - Queries oracle OHLC for symbol, places mean-reverting orders towards fundamental close.
    - Falls back to random reference when oracle off.
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
        self._submit_towards(sym, float(np.random.uniform(20, 80)))

    def receive(self, message):
        super().receive(message)
        keep = []
        for m in self.inbox:
            if m.message_type == MessageType.ORACLE_RESPONSE_OHLC and isinstance(m.content, dict):
                sym = str(m.content.get("symbol"))
                data = m.content.get("ohlc") or {}
                try:
                    close = data.get("close")
                    if close is not None and close != "":
                        self._submit_towards(sym, float(close))
                except Exception:
                    pass
            else:
                keep.append(m)
        self.inbox = keep

    def _submit_towards(self, symbol: str, ref: float):
        # Buy below ref, sell above if inventory
        buy_px = round(max(0.01, ref * (1.0 - 0.003)), 2)
        reqs = [
            {
                "type": "limit_order",
                "symbol": symbol,
                "agent_id": self.id,
                "timestamp": str(self.current_time),
                "side": "buy",
                "quantity": int(np.random.randint(1, 40)),
                "price": buy_px,
            }
        ]
        inv = int(self.portfolio.holdings.get(symbol, 0))
        if inv > 0:
            qty = max(1, min(int(np.random.randint(1, 40)), inv))
            sell_px = round(ref * (1.0 + 0.003), 2)
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

