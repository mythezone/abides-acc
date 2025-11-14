from typing import Dict, List, Optional, Tuple
from core.order import Order, LimitOrder


class PreopenOrderBook:
    """
    Minimal pre-open call auction order book.

    - Stores orders without continuous matching.
    - Supports cancellation by order_id in allowed window.
    - Aggregates by price levels to compute indicative book and clearing price.
    - At auction end, matches at the clearing price to maximize executable volume
      and minimize imbalance (standard call auction heuristic).
    """

    def __init__(self, stock: str):
        self.stock = stock
        self._orders: List[Optional[Order]] = []
        self._id_index: Dict[str, int] = {}

    def add_order(self, order: Order):
        self._id_index[order.id] = len(self._orders)
        self._orders.append(order)

    def cancel_order(self, order_id: str):
        idx = self._id_index.pop(order_id, None)
        if idx is not None and 0 <= idx < len(self._orders):
            self._orders[idx] = None

    def _aggregate_levels(self) -> Tuple[Dict[float, int], Dict[float, int], int, int]:
        bids: Dict[float, int] = {}
        asks: Dict[float, int] = {}
        mkt_buy = 0
        mkt_sell = 0
        for o in self._orders:
            if o is None:
                continue
            price = getattr(o, "price", None)
            qty = int(getattr(o, "quantity", 0))
            side = getattr(o, "side", None)
            if price is None:
                # market order
                if side == "buy":
                    mkt_buy += qty
                elif side == "sell":
                    mkt_sell += qty
            else:
                p = float(price)
                if side == "buy":
                    bids[p] = int(bids.get(p, 0)) + qty
                elif side == "sell":
                    asks[p] = int(asks.get(p, 0)) + qty
        return bids, asks, mkt_buy, mkt_sell

    def snapshot_top_n(self, n: int = 5):
        bids, asks, _, _ = self._aggregate_levels()
        bid_lvls = sorted(bids.items(), key=lambda x: -x[0])[:n]
        ask_lvls = sorted(asks.items(), key=lambda x: x[0])[:n]
        return {"buy": bid_lvls, "sell": ask_lvls}

    def compute_clearing_price(self) -> Optional[Tuple[float, int, int]]:
        bids, asks, mkt_buy, mkt_sell = self._aggregate_levels()
        if not bids or not asks:
            return None
        candidates = sorted(set(list(bids.keys()) + list(asks.keys())))

        def executable(px: float) -> Tuple[int, int]:
            cb = mkt_buy + sum(q for p, q in bids.items() if p >= px)
            cs = mkt_sell + sum(q for p, q in asks.items() if p <= px)
            return min(cb, cs), cb - cs

        best_v = -1
        best_imb = 1 << 30
        best_px = candidates[0]
        for px in candidates:
            v, imb = executable(px)
            if v > best_v or (v == best_v and abs(imb) < abs(best_imb)):
                best_v, best_imb, best_px = v, imb, px
        return float(best_px), int(best_v), int(best_imb)

    def match_at_clearing(self) -> Tuple[List[dict], List[Order]]:
        """Produce trades at the computed clearing price and return remaining orders
        to be carried into the continuous book.
        """
        res = self.compute_clearing_price()
        if res is None:
            # No crossing; carry all remaining (limit) orders to book
            remaining = [o for o in self._orders if o is not None and getattr(o, "price", None) is not None]
            self._orders = []
            self._id_index = {}
            return [], remaining
        px, _, _ = res
        buys = [o for o in self._orders if o is not None and getattr(o, "side", None) == "buy" and (getattr(o, "price", px) is None or float(getattr(o, "price", px)) >= px)]
        sells = [o for o in self._orders if o is not None and getattr(o, "side", None) == "sell" and (getattr(o, "price", px) is None or float(getattr(o, "price", px)) <= px)]
        # Sort: buys by price desc, sells by price asc. Preopen assumed FIFO within same price (list order)
        buys.sort(key=lambda o: -(float(getattr(o, "price", px)) if getattr(o, "price", None) is not None else px))
        sells.sort(key=lambda o: (float(getattr(o, "price", px)) if getattr(o, "price", None) is not None else px))
        trades: List[dict] = []
        bi, si = 0, 0
        while bi < len(buys) and si < len(sells):
            b = buys[bi]
            s = sells[si]
            qty = min(int(b.quantity), int(s.quantity))
            if qty <= 0:
                if int(b.quantity) <= 0:
                    bi += 1
                if int(s.quantity) <= 0:
                    si += 1
                continue
            trades.append({
                "stock": self.stock,
                "price": float(px),
                "quantity": int(qty),
                "buy": b.agent_id,
                "sell": s.agent_id,
            })
            b.quantity = int(b.quantity) - qty
            s.quantity = int(s.quantity) - qty
            if int(b.quantity) <= 0:
                bi += 1
            if int(s.quantity) <= 0:
                si += 1
        # Remaining (limit) orders carry into continuous book
        remaining: List[Order] = []
        for o in self._orders:
            if o is None:
                continue
            if getattr(o, "price", None) is not None and int(getattr(o, "quantity", 0)) > 0:
                remaining.append(o)
        # reset preopen
        self._orders = []
        self._id_index = {}
        return trades, remaining

