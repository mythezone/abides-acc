import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Union

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

    def __init__(self, id, *args, initial_stocks: Optional[List[Union[str, Dict]]] = None, **kwargs):
        super().__init__(id, *args, **kwargs)
        self.subscribed_stocks: List[str] = []
        if initial_stocks:
            for sym in initial_stocks:
                if isinstance(sym, str):
                    self.subscribed_stocks.append(sym)
                elif isinstance(sym, dict):
                    val = sym.get("stock")
                    if val:
                        self.subscribed_stocks.append(str(val))
        # BG agents place more frequent but smaller orders by default
        if not hasattr(self, "wakeup_ms_range"):
            self.wakeup_ms_range = [30, 80]
        if not hasattr(self, "agent_log_freq"):
            self.agent_log_freq = "tick"
        # Configuration knobs (with sensible defaults) controllable from config params
        self.min_orders_per_stock = int(kwargs.pop("min_orders_per_stock", 3))
        self.max_orders_per_stock = int(kwargs.pop("max_orders_per_stock", 7))
        if self.max_orders_per_stock < self.min_orders_per_stock:
            self.max_orders_per_stock = self.min_orders_per_stock
        self.min_quantity = int(kwargs.pop("min_quantity", 20))
        self.max_quantity = int(kwargs.pop("max_quantity", 120))
        if self.max_quantity < self.min_quantity:
            self.max_quantity = self.min_quantity
        self.price_tick = float(kwargs.pop("price_tick", 0.01))
        self.max_levels = int(kwargs.pop("max_levels", 10))
        self.market_order_prob = float(kwargs.pop("market_order_prob", 0.05))
        self.bias_empty_side = float(kwargs.pop("bias_empty_side", 0.75))
        self.stock_batch_min = int(kwargs.pop("min_stocks_per_batch", 2))
        self.stock_batch_max = int(kwargs.pop("max_stocks_per_batch", 6))
        self.stock_batch_max = max(self.stock_batch_min, self.stock_batch_max)
        self._latest_snapshots: Dict[str, Dict[str, float]] = {}

    # override to ignore portfolio updates & fees
    def process_inbox(self):
        new_stocks: List[str] = []
        for m in self.inbox:
            if m.message_type == MessageType.MKT_DATA and isinstance(m.content, dict):
                if "stocks" in m.content:
                    for entry in m.content.get("stocks", []):
                        sym = self._normalize_stock(entry)
                        if sym:
                            new_stocks.append(sym)
                else:
                    stock = self._normalize_stock(m.content.get("stock"))
                    if stock:
                        snapshot = {
                            "best_bid": m.content.get("best_bid"),
                            "best_ask": m.content.get("best_ask"),
                            "mid": m.content.get("mid"),
                            "ts": m.content.get("ts"),
                        }
                        self._latest_snapshots[stock] = snapshot
            elif m.message_type == MessageType.ORACLE_RESPONSE_LOB and isinstance(m.content, dict):
                stock = self._normalize_stock(m.content.get("stock"))
                data = m.content.get("lob")
                if stock:
                    reqs = self._orders_from_oracle_lob(stock, data or {})
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
        if new_stocks:
            merged = self.subscribed_stocks + new_stocks
            # Preserve order while removing duplicates
            seen = set()
            self.subscribed_stocks = []
            for sym in merged:
                if sym not in seen:
                    self.subscribed_stocks.append(sym)
                    seen.add(sym)

    def _normalize_stock(self, value) -> Optional[str]:
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            raw = value.get("stock")
            if raw:
                return str(raw)
        if value is not None:
            return str(value)
        return None

    def _request_top_of_book(self, stocks: List[str]) -> None:
        if not stocks:
            return
        requests = [{"stock": sym, "depth": 1} for sym in stocks]
        msg = new_message(
            message_type=MessageType.MKT_DATA,
            sender_id=self.id,
            recipient_id="Exchange",
            send_time=self.current_time,
            recive_time=self.current_time,
            content={"requests": requests},
        )
        self.send(msg)

    def action(self):
        # subscribe if needed
        if not self.subscribed_stocks:
            n = int(np.random.randint(3, 8))
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
            return

        # In calibration mode, always ping oracle for LOB and follow
        if getattr(self, "calibration_mode", False) and self.oracle_id:
            sym = str(np.random.choice(self.subscribed_stocks))
            self.request_oracle(sym, kind="lob")
            return

        # Otherwise, send richer batch of limit orders across multiple stocks
        batch_lo = min(self.stock_batch_min, len(self.subscribed_stocks))
        batch_hi = min(self.stock_batch_max, len(self.subscribed_stocks))
        if batch_hi <= 0:
            return
        batch_sz = int(np.random.randint(batch_lo, batch_hi + 1))
        selected = list(np.random.choice(self.subscribed_stocks, batch_sz, replace=False))

        # Request fresh top-of-book snapshots for selected stocks (async for next wakeup)
        self._request_top_of_book(selected)

        reqs = []
        for stock in selected:
            reqs.extend(self._generate_stock_orders(stock))
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
    def _orders_from_oracle_lob(self, stock: str, data: dict):
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
                    "type": "limit_order", "stock": stock, "agent_id": self.id,
                    "timestamp": str(self.current_time), "side": "buy", "quantity": qty,
                    "price": best_bid
                })
            if best_ask is not None:
                qty = max(1, int(0.3 * max(1, best_ask_vol)))
                reqs.append({
                    "type": "limit_order", "stock": stock, "agent_id": self.id,
                    "timestamp": str(self.current_time), "side": "sell", "quantity": qty,
                    "price": best_ask
                })
        except Exception:
            pass
        return reqs
    def _generate_stock_orders(self, stock: str) -> List[Dict]:
        snapshot = self._latest_snapshots.get(stock, {})
        raw_best_bid = snapshot.get("best_bid")
        raw_best_ask = snapshot.get("best_ask")
        raw_mid = snapshot.get("mid")

        def _to_float(val):
            try:
                if val is None or (isinstance(val, float) and np.isnan(val)):
                    return None
                return float(val)
            except Exception:
                return None

        best_bid = _to_float(raw_best_bid)
        best_ask = _to_float(raw_best_ask)
        mid = _to_float(raw_mid)
        need_buy_boost = best_bid is None
        need_sell_boost = best_ask is None

        if best_bid is None and best_ask is None:
            if mid is None:
                mid = float(np.random.uniform(10.0, 100.0))
            best_bid = mid - self.price_tick
            best_ask = mid + self.price_tick
        elif best_bid is None:
            best_bid = float(best_ask) - self.price_tick
            if mid is None:
                mid = best_bid + self.price_tick
        elif best_ask is None:
            best_ask = float(best_bid) + self.price_tick
            if mid is None:
                mid = best_bid + self.price_tick
        if mid is None and best_bid is not None and best_ask is not None:
            mid = (float(best_bid) + float(best_ask)) / 2.0

        orders: List[Dict] = []
        n_orders = int(np.random.randint(self.min_orders_per_stock, self.max_orders_per_stock + 1))
        buy_orders = n_orders // 2
        sell_orders = n_orders - buy_orders
        if need_buy_boost and buy_orders == 0:
            buy_orders = 1
        if need_sell_boost and sell_orders == 0:
            sell_orders = 1
        total = buy_orders + sell_orders
        if total < n_orders:
            remaining = n_orders - total
            prob_buy = 0.5
            if need_buy_boost and not need_sell_boost:
                prob_buy = max(self.bias_empty_side, 0.5)
            elif need_sell_boost and not need_buy_boost:
                prob_buy = min(1.0 - self.bias_empty_side, 0.5)
            for _ in range(remaining):
                if np.random.rand() < prob_buy:
                    buy_orders += 1
                else:
                    sell_orders += 1
        elif total > n_orders:
            # Trim excess while keeping at least one order on required sides
            excess = total - n_orders
            while excess > 0:
                if sell_orders > 1 and (not need_sell_boost or sell_orders - 1 >= 1):
                    sell_orders -= 1
                elif buy_orders > 1 and (not need_buy_boost or buy_orders - 1 >= 1):
                    buy_orders -= 1
                else:
                    break
                excess -= 1
        sides: List[str] = ["buy"] * buy_orders + ["sell"] * sell_orders
        np.random.shuffle(sides)

        for side in sides:
            quantity = int(np.random.randint(self.min_quantity, self.max_quantity + 1))
            order_type = "limit_order"
            if np.random.rand() < self.market_order_prob:
                order_type = "market_order"
            price = None
            if order_type == "limit_order":
                level = int(np.random.randint(0, max(self.max_levels, 1)))
                if side == "buy":
                    base = best_bid if best_bid is not None else (mid - self.price_tick)
                    price = max(self.price_tick, float(base) - level * self.price_tick)
                else:
                    base = best_ask if best_ask is not None else (mid + self.price_tick)
                    price = max(self.price_tick, float(base) + level * self.price_tick)
                price = round(price, 4)
            order = {
                "type": order_type,
                "stock": stock,
                "agent_id": self.id,
                "timestamp": str(self.current_time),
                "side": side,
                "quantity": quantity,
            }
            if price is not None:
                order["price"] = price
            orders.append(order)
        return orders
