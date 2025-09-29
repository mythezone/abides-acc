import numpy as np
from typing import List, Optional

from core.agent.base import BaseAgent
from core.message import MessageType, new_message


class HeuristicBeliefLearningAgent(BaseAgent):
    """
    Lightweight adapter approximating ABIDES HBL behavior.

    - Queries top-of-book then places a small order near best side, alternating for diversification.
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
        self._last_side: str = "sell"

    def action(self):
        if not self.subscribed_symbols:
            return
        sym = str(np.random.choice(self.subscribed_symbols))
        import pandas as pd
        ts = self.current_time if isinstance(self.current_time, pd.Timestamp) else pd.Timestamp.now()
        msg = new_message(
            message_type=MessageType.QUERY_SPERAD,
            sender_id=self.id,
            recipient_id="Exchange",
            send_time=ts,
            recive_time=ts,
            content={"symbol": sym, "depth": 1},
        )
        self.send(msg)

    def handle_inbox_message(self, message):
        if message.message_type == MessageType.QUERY_SPERAD and isinstance(message.content, dict):
            sym = str(message.content.get("symbol"))
            bids = message.content.get("bids", [])
            asks = message.content.get("asks", [])
            if not (bids or asks):
                return True
            side = "buy" if self._last_side == "sell" else "sell"
            self._last_side = side
            price = None
            if side == "buy" and bids:
                price = float(bids[0][0])
            elif side == "sell" and asks:
                price = float(asks[0][0])
            qty = int(np.random.randint(1, 30))
            inv = int(self.portfolio.holdings.get(sym, 0))
            if side == "sell" and inv <= 0:
                side = "buy"
            if side == "sell":
                qty = max(1, min(qty, inv))
            import pandas as pd
            ts2 = self.current_time if isinstance(self.current_time, pd.Timestamp) else pd.Timestamp.now()
            req = {
                "type": "limit_order",
                "symbol": sym,
                "agent_id": self.id,
                "timestamp": str(ts2),
                "side": side,
                "quantity": qty,
            }
            if price is not None:
                req["price"] = price
            self.send(
                new_message(
                    message_type=MessageType.SUBMIT_ORDER,
                    sender_id=self.id,
                    recipient_id="Exchange",
                    send_time=ts2,
                    recive_time=ts2,
                    content={"requests": [req]},
                )
            )
            return True
        return super().handle_inbox_message(message)
