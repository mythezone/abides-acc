from core.agent.base import BaseAgent
from core.message import MessageType, MessageQueue, new_message
from typing import List
import numpy as np
import pandas as pd


class ZeroIntelligenceAgent(BaseAgent):

    def __init__(self, id, *args, message_queue: MessageQueue = None, initial_stocks: List[str] = None, **kwargs):
        super().__init__(id, *args, message_queue=message_queue, **kwargs)
        self.subscribed_stocks: List[str] = []
        if initial_stocks:
            for sym in initial_stocks:
                if isinstance(sym, str):
                    self.subscribed_stocks.append(sym)
                elif isinstance(sym, dict):
                    val = sym.get("stock")
                    if val:
                        self.subscribed_stocks.append(str(val))

    def action(self):
        # Detect SZSE pre-open auction window (09:15-09:25)
        preopen = False
        try:
            to = pd.to_datetime(self.current_time).time()
            preopen = (pd.Timestamp("09:15").time() <= to < pd.Timestamp("09:25").time())
        except Exception:
            preopen = False

        if not self.subscribed_stocks:
            n = int(np.random.randint(1, 5))
            request = {"type": "query_stocks", "n": n}
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
            # Pre-open auction: submit fewer limit orders, avoid market orders and cancellations
            if preopen:
                selected = list(np.random.choice(self.subscribed_stocks, int(np.random.randint(1, 3)), replace=False))
                reqs = []
                for stock in selected:
                    side = np.random.choice(["buy", "sell"]) 
                    # only allow sell if we have inventory
                    inv = int(self.portfolio.holdings.get(stock, 0))
                    if side == "sell" and inv <= 0:
                        side = "buy"
                    quantity = int(np.random.randint(1, 50))
                    if side == "sell" and inv > 0:
                        quantity = max(1, min(quantity, inv))
                    price = round(float(np.random.uniform(10, 100)), 2)
                    order = {
                        "type": "limit_order",
                        "stock": stock,
                        "agent_id": self.id,
                        "timestamp": str(self.current_time),
                        "side": side,
                        "quantity": quantity,
                        "price": price,
                    }
                    # Skip zero-quantity sells
                    if side != "sell" or quantity > 0:
                        reqs.append(order)
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
                return
            # Calibration mode: query oracle first, optionally craft orders around oracle snapshot
            if getattr(self, "calibration_mode", False) and self.oracle_id:
                sym = str(np.random.choice(self.subscribed_stocks))
                self.request_oracle(sym, kind="lob")
                # orders will be sent after oracle response is processed
                return
            # Normal mode: batch multiple orders into a single message to reduce overhead
            batch_sz = int(np.random.randint(1, min(10, len(self.subscribed_stocks)) + 1))
            selected = list(np.random.choice(self.subscribed_stocks, batch_sz, replace=False))
            reqs = []
            for stock in selected:
                side = np.random.choice(["buy", "sell"]) 
                inv = int(self.portfolio.holdings.get(stock, 0))
                if side == "sell" and inv <= 0:
                    side = "buy"
                quantity = int(np.random.randint(1, 100))
                if side == "sell" and inv > 0:
                    quantity = max(1, min(quantity, inv))
                price = round(float(np.random.uniform(10, 100)), 2)
                order_type = np.random.choice(["limit_order", "market_order"])
                order = {
                    "type": order_type,
                    "stock": stock,
                    "agent_id": self.id,
                    "timestamp": str(self.current_time),
                    "side": side,
                    "quantity": quantity,
                }
                if order_type == "limit_order":
                    order["price"] = price
                if side != "sell" or quantity > 0:
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
        # Then pick up stock list if provided
        new_stocks: List[str] = []
        keep = []

        def _normalize_stock(value):
            if isinstance(value, str):
                return value
            if isinstance(value, dict):
                sym = value.get("stock")
                if sym is not None:
                    return str(sym)
            return None

        for m in self.inbox:
            if m.message_type == MessageType.MKT_DATA and isinstance(m.content, dict):
                if "stocks" in m.content:
                    for item in m.content.get("stocks", []):
                        sym = _normalize_stock(item)
                        if sym:
                            new_stocks.append(sym)
            elif (
                m.message_type == MessageType.ORACLE_RESPONSE_LOB
                and isinstance(m.content, dict)
            ):
                data = m.content.get("lob") or {}
                if not isinstance(data, dict) or not data:
                    continue
                stock = m.content.get("stock")
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
                        # buy leg
                        reqs.append({
                            "type": "limit_order", "stock": stock, "agent_id": self.id,
                            "timestamp": str(self.current_time), "side": "buy", "quantity": int(np.random.randint(1, 50)),
                            "price": best_bid
                        })
                        # sell leg only if inventory is available
                        inv = int(self.portfolio.holdings.get(stock, 0))
                        if inv > 0:
                            qty = max(1, min(int(np.random.randint(1, 50)), inv))
                            reqs.append({
                                "type": "limit_order", "stock": stock, "agent_id": self.id,
                                "timestamp": str(self.current_time), "side": "sell", "quantity": qty,
                                "price": best_ask
                            })
                        # mid buy
                        reqs.append({
                            "type": "limit_order", "stock": stock, "agent_id": self.id,
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
            elif m.message_type == MessageType.ORACLE_RESPONSE_OHLC and isinstance(m.content, dict):
                data = m.content.get("ohlc") or {}
                stock = m.content.get("stock")
                reqs = []
                try:
                    close = data.get("close") or data.get("close")
                    if close is not None and close != "":
                        close = float(close)
                        # place buy/sell around close
                        reqs.append({
                            "type": "limit_order", "stock": stock, "agent_id": self.id,
                            "timestamp": str(self.current_time), "side": "buy", "quantity": int(np.random.randint(1, 50)),
                            "price": close
                        })
                        inv = int(self.portfolio.holdings.get(stock, 0))
                        if inv > 0:
                            qty = max(1, min(int(np.random.randint(1, 50)), inv))
                            reqs.append({
                                "type": "limit_order", "stock": stock, "agent_id": self.id,
                                "timestamp": str(self.current_time), "side": "sell", "quantity": qty,
                                "price": close
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
        if new_stocks:
            # Deduplicate and ensure all entries are strings
            uniq = []
            for sym in new_stocks:
                if sym not in uniq:
                    uniq.append(sym)
            self.subscribed_stocks = uniq
