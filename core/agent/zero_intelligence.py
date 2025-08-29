from core.agent.base import BaseAgent
from core.message import MessageType, MessageQueue, new_message
from typing import List
import numpy as np
import pandas as pd


class ZeroIntelligenceAgent(BaseAgent):

    def __init__(self, id, *args, message_queue: MessageQueue = None, initial_symbols: List[str] = None, **kwargs):
        super().__init__(id, *args, message_queue=message_queue, **kwargs)
        self.subscribed_symbols: List[str] = (initial_symbols or [])[:]

    def action(self):
        if not self.subscribed_symbols:
            n = int(np.random.randint(1, 5))
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
        else:
            # Calibration mode: query oracle first, optionally craft orders around oracle snapshot
            if getattr(self, "calibration_mode", False) and self.oracle_id:
                sym = str(np.random.choice(self.subscribed_symbols))
                self.request_oracle(sym, kind="lob")
                # orders will be sent after oracle response is processed
                return
            # Normal mode: batch multiple orders into a single message to reduce overhead
            batch_sz = int(np.random.randint(1, min(5, len(self.subscribed_symbols)) + 1))
            selected = list(np.random.choice(self.subscribed_symbols, batch_sz, replace=False))
            reqs = []
            for symbol in selected:
                side = np.random.choice(["buy", "sell"]) 
                quantity = int(np.random.randint(1, 100))
                price = round(float(np.random.uniform(10, 100)), 2)
                order_type = np.random.choice(["limit_order", "market_order"])
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

    def process_inbox(self):
        # First apply base processing (portfolio updates)
        super().process_inbox()
        # Then pick up symbol list if provided
        new_symbols = []
        keep = []
        for m in self.inbox:
            if m.message_type == MessageType.MKT_DATA and isinstance(m.content, dict):
                if "symbols" in m.content:
                    new_symbols.extend(m.content.get("symbols", []))
            elif m.message_type == MessageType.ORACLE_RESPONSE_LOB and isinstance(m.content, dict):
                data = m.content.get("lob")
                symbol = m.content.get("symbol")
                # build simple heuristic orders near oracle best levels
                reqs = []
                try:
                    # Columns are: kernel_time, AskPrice0..AskVolume..BidPrice..BidVolume..
                    best_ask = None
                    best_bid = None
                    # Find first non-empty ask/bid price columns
                    for k in data.keys():
                        if str(k).startswith("AskPrice0") or str(k) == "AskPrice0":
                            val = data[k]
                            if pd.notna(val) and val != "":
                                best_ask = float(val)
                                break
                    for k in data.keys():
                        if str(k).startswith("BidPrice0") or str(k) == "BidPrice0":
                            val = data[k]
                            if pd.notna(val) and val != "":
                                best_bid = float(val)
                                break
                    if best_ask is not None and best_bid is not None:
                        mid = round((best_ask + best_bid) / 2.0, 2)
                        # Place small aggressive orders around oracle implied levels
                        reqs.append({
                            "type": "limit_order", "symbol": symbol, "agent_id": self.id,
                            "timestamp": str(self.current_time), "side": "buy", "quantity": int(np.random.randint(1, 50)),
                            "price": best_bid
                        })
                        reqs.append({
                            "type": "limit_order", "symbol": symbol, "agent_id": self.id,
                            "timestamp": str(self.current_time), "side": "sell", "quantity": int(np.random.randint(1, 50)),
                            "price": best_ask
                        })
                        reqs.append({
                            "type": "limit_order", "symbol": symbol, "agent_id": self.id,
                            "timestamp": str(self.current_time), "side": "buy", "quantity": int(np.random.randint(1, 20)),
                            "price": mid
                        })
                except Exception:
                    pass
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
            else:
                keep.append(m)
        self.inbox = keep
        if new_symbols:
            # Deduplicate
            uniq = list(dict.fromkeys(new_symbols))
            self.subscribed_symbols = uniq
