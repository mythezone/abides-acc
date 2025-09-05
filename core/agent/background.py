import numpy as np
import pandas as pd
from typing import List, Optional

from core.agent.base import BaseAgent
from core.message import MessageType, new_message


class BackgroundAgent(BaseAgent):
    """
    Background liquidity agent that:
    - does NOT manage portfolio (ignores executions and fees)
    - is exempt from T+1 (exchange will treat sender_id starting with 'background_' as exempt)
    - generates random order flow to keep books active
    - in calibration mode, follows oracle LOB to emulate target microstructure
    """

    def __init__(self, id, *args, initial_symbols: Optional[List[str]] = None, **kwargs):
        super().__init__(id, *args, **kwargs)
        self.subscribed_symbols: List[str] = (initial_symbols or [])[:]
        # BG agents place more frequent but smaller orders by default
        if not hasattr(self, "wakeup_ms_range"):
            self.wakeup_ms_range = [30, 80]
        if not hasattr(self, "agent_log_freq"):
            self.agent_log_freq = "tick"

    # override to ignore portfolio updates & fees
    def process_inbox(self):
        keep = []
        for m in self.inbox:
            if m.message_type in (MessageType.ORACLE_RESPONSE_LOB, MessageType.MKT_DATA):
                keep.append(m)
        self.inbox = keep

    def action(self):
        # subscribe if needed
        if not self.subscribed_symbols:
            n = int(np.random.randint(3, 8))
            request = {"type": "query_symbols", "n": n}
            msg = new_message(
                message_type=MessageType.MKT_DATA,
                sender_id=self.id,
                recipient_id="Exchange",
                send_time=self.current_time,
                recive_time=self.current_time,
                content=request,
            )
            self.send(msg)
            return

        # In calibration mode, always ping oracle for LOB and follow
        if getattr(self, "calibration_mode", False) and self.oracle_id:
            sym = str(np.random.choice(self.subscribed_symbols))
            self.request_oracle(sym, kind="lob")
            return

        # Otherwise, send random batch of orders (both sides allowed)
        batch_sz = int(np.random.randint(3, min(12, len(self.subscribed_symbols)) + 1))
        selected = list(np.random.choice(self.subscribed_symbols, batch_sz, replace=False))
        reqs = []
        for symbol in selected:
            side = np.random.choice(["buy", "sell"]) 
            quantity = int(np.random.randint(1, 60))
            price = round(float(np.random.uniform(10, 100)), 2)
            order_type = np.random.choice(["limit_order", "market_order"], p=[0.8, 0.2])
            order = {
                "type": order_type,
                "symbol": symbol,
                "agent_id": self.id,
                "timestamp": str(self.current_time),
                "side": side,
                "quantity": quantity,
            }
            if order_type == "limit_order":
                order["price"] = price
            reqs.append(order)
        msg = new_message(
            message_type=MessageType.SUBMIT_ORDER,
            sender_id=self.id,
            recipient_id="Exchange",
            send_time=self.current_time,
            recive_time=self.current_time,
            content={"requests": reqs},
        )
        self.send(msg)

    # BG follows oracle response aggressively
    def _orders_from_oracle_lob(self, symbol: str, data: dict):
        reqs = []
        try:
            # try to read top-of-book
            best_ask = None
            best_ask_vol = 0
            best_bid = None
            best_bid_vol = 0
            for k, v in data.items():
                if str(k).startswith("AskPrice0"):
                    if pd.notna(v) and v != "":
                        best_ask = float(v)
                if str(k).startswith("AskVolume0"):
                    if pd.notna(v) and v != "":
                        best_ask_vol = int(v)
                if str(k).startswith("BidPrice0"):
                    if pd.notna(v) and v != "":
                        best_bid = float(v)
                if str(k).startswith("BidVolume0"):
                    if pd.notna(v) and v != "":
                        best_bid_vol = int(v)
            if best_bid is not None:
                qty = max(1, int(0.3 * max(1, best_bid_vol)))
                reqs.append({
                    "type": "limit_order", "symbol": symbol, "agent_id": self.id,
                    "timestamp": str(self.current_time), "side": "buy", "quantity": qty,
                    "price": best_bid
                })
            if best_ask is not None:
                qty = max(1, int(0.3 * max(1, best_ask_vol)))
                reqs.append({
                    "type": "limit_order", "symbol": symbol, "agent_id": self.id,
                    "timestamp": str(self.current_time), "side": "sell", "quantity": qty,
                    "price": best_ask
                })
        except Exception:
            pass
        return reqs

    def process_inbox(self):
        # Override: do not apply executions to portfolio
        new_syms = []
        for m in self.inbox:
            if m.message_type == MessageType.MKT_DATA and isinstance(m.content, dict):
                if "symbols" in m.content:
                    new_syms.extend(m.content.get("symbols", []))
            elif m.message_type == MessageType.ORACLE_RESPONSE_LOB and isinstance(m.content, dict):
                data = m.content.get("lob")
                symbol = m.content.get("symbol")
                reqs = self._orders_from_oracle_lob(symbol, data or {})
                if reqs:
                    msg = new_message(
                        message_type=MessageType.SUBMIT_ORDER,
                        sender_id=self.id,
                        recipient_id="Exchange",
                        send_time=self.current_time,
                        recive_time=self.current_time,
                        content={"requests": reqs},
                    )
                    self.send(msg)
        self.inbox = []
        if new_syms:
            self.subscribed_symbols = list(dict.fromkeys(new_syms))

