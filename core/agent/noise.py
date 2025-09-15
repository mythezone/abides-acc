import numpy as np
import pandas as pd
from typing import List, Optional

from core.agent.base import BaseAgent
from core.message import MessageType, new_message


class NoiseAgent(BaseAgent):
    """
    ABIDES-style NoiseAgent adapter.

    - On wakeup, randomly submits small limit/market orders across initial symbols.
    - Compatible with our SUBMIT_ORDER batching and portfolio updates via BaseAgent.
    """

    def __init__(
        self,
        id: str,
        *args,
        initial_symbols: Optional[List[str]] = None,
        max_batch: int = 3,
        **kwargs,
    ):
        super().__init__(id, *args, **kwargs)
        self.subscribed_symbols: List[str] = (initial_symbols or [])[:]
        self.max_batch = int(max_batch)

    def action(self):
        if not self.subscribed_symbols:
            return
        # Ensure sample size <= population for replace=False
        k = len(self.subscribed_symbols)
        if k <= 0:
            return
        n = int(np.random.randint(1, min(self.max_batch, k) + 1))
        selected = list(np.random.choice(self.subscribed_symbols, n, replace=False))
        ts = self.current_time if isinstance(self.current_time, pd.Timestamp) else pd.Timestamp.now()
        reqs = []
        for symbol in selected:
            side = np.random.choice(["buy", "sell"])  # portfolio will guard negative sells
            inv = int(self.portfolio.holdings.get(symbol, 0))
            qty = int(np.random.randint(1, 50))
            if side == "sell" and inv <= 0:
                side = "buy"
            if side == "sell" and inv > 0:
                qty = max(1, min(qty, inv))
            price = round(float(np.random.uniform(10, 100)), 2)
            otype = np.random.choice(["limit_order", "market_order"])  # ABIDES style
            order = {
                "type": otype,
                "symbol": symbol,
                "agent_id": self.id,
                "timestamp": str(ts),
                "side": side,
                "quantity": qty,
            }
            if otype == "limit_order":
                order["price"] = price
            if side != "sell" or qty > 0:
                reqs.append(order)
        if not reqs:
            return
        msg = new_message(
            message_type=MessageType.SUBMIT_ORDER,
            sender_id=self.id,
            recipient_id="Exchange",
            send_time=ts,
            recive_time=ts,
            content={"requests": reqs},
        )
        self.send(msg)
