import numpy as np
from typing import List, Optional

from core.agent.base import BaseAgent
from core.message import MessageType, new_message


class OrderBookImbalanceAgent(BaseAgent):
    """
    ABIDES-style OrderBookImbalanceAgent adapter.

    - Queries top-of-book (QUERY_SPERAD) and submits orders biased by imbalance.
    """

    def __init__(
        self,
        id: str,
        *args,
        initial_symbols: Optional[List[str]] = None,
        depth: int = 1,
        **kwargs,
    ):
        super().__init__(id, *args, **kwargs)
        self.subscribed_symbols: List[str] = (initial_symbols or [])[:]
        self.depth = int(depth)

    def action(self):
        if not self.subscribed_symbols:
            return
        sym = str(np.random.choice(self.subscribed_symbols))
        ts = self.current_time if hasattr(self, 'current_time') else None
        ts = ts if isinstance(ts, __import__('pandas').Timestamp) else __import__('pandas').Timestamp.now()
        msg = new_message(
            message_type=MessageType.QUERY_SPERAD,
            sender_id=self.id,
            recipient_id="Exchange",
            send_time=ts,
            recive_time=ts,
            content={"symbol": sym, "depth": self.depth},
        )
        self.send(msg)

    def receive(self, message):
        super().receive(message)
        keep = []
        for m in self.inbox:
            if m.message_type == MessageType.QUERY_SPERAD and isinstance(m.content, dict):
                sym = str(m.content.get("symbol"))
                bids = m.content.get("bids", [])
                asks = m.content.get("asks", [])
                if bids or asks:
                    bvol = sum(int(x[1]) for x in bids)
                    avol = sum(int(x[1]) for x in asks)
                    side = "buy" if bvol <= avol else "sell"
                    price = None
                    if side == "buy":
                        price = float(bids[0][0]) if bids else (float(asks[0][0]) if asks else None)
                    else:
                        price = float(asks[0][0]) if asks else (float(bids[0][0]) if bids else None)
                    qty = int(np.random.randint(1, 50))
                    inv = int(self.portfolio.holdings.get(sym, 0))
                    if side == "sell" and inv <= 0:
                        side = "buy"
                    if side == "sell":
                        qty = max(1, min(qty, inv))
                    ts2 = self.current_time if hasattr(self, 'current_time') else None
                    import pandas as pd
                    ts2 = ts2 if isinstance(ts2, pd.Timestamp) else pd.Timestamp.now()
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
            else:
                keep.append(m)
        self.inbox = keep
