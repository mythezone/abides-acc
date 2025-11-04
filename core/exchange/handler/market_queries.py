from typing import List

import pandas as pd

from core.message import MessageType, new_message

from .manager import register_handler


@register_handler(
    MessageType.MKT_DATA,
    MessageType.QUERY_LAST_TRADE,
    MessageType.QUERY_SPERAD,
    MessageType.QUERY_ORDER_STREAM,
    MessageType.QUERY_TRANSACTED_VOLUME,
    MessageType.QUERY_FUNDAMENTAL,
    MessageType.QUERY_TOP_OF_BOOK,
)
def handle(exchange, message, now):
    msg_type = message.message_type
    if msg_type == MessageType.MKT_DATA:
        return _handle_market_data(exchange, message, now)
    if msg_type == MessageType.QUERY_LAST_TRADE:
        symbol = message.content.get("symbol")
        if not isinstance(symbol, str):
            symbol = None
        price = exchange._last_price.get(symbol) if isinstance(symbol, str) else None
        return [
            new_message(
                message_type=MessageType.QUERY_LAST_TRADE,
                sender_id="Exchange",
                recipient_id=message.sender_id,
                send_time=now,
                recive_time=now,
                content={"symbol": symbol, "data": price, "mkt_closed": not exchange.is_open},
            )
        ]
    if msg_type == MessageType.QUERY_SPERAD:
        symbol = message.content.get("symbol")
        if not isinstance(symbol, str):
            symbol = None
        depth = int(message.content.get("depth", 1))
        bids: List = []
        asks: List = []
        lob = exchange._get_lob(symbol)
        if lob is not None:
            snap = lob.snapshot_top_n(depth)
            bids = snap.get("buy", [])
            asks = snap.get("sell", [])
        return [
            new_message(
                message_type=MessageType.QUERY_SPERAD,
                sender_id="Exchange",
                recipient_id=message.sender_id,
                send_time=now,
                recive_time=now,
                content={
                    "symbol": symbol,
                    "depth": depth,
                    "bids": bids,
                    "asks": asks,
                    "data": exchange._last_price.get(symbol) if isinstance(symbol, str) else None,
                    "mkt_closed": not exchange.is_open,
                    "book": "",
                },
            )
        ]
    if msg_type == MessageType.QUERY_ORDER_STREAM:
        symbol = message.content.get("symbol")
        if not isinstance(symbol, str):
            symbol = None
        length = int(message.content.get("length", 10))
        orders = []
        lob = exchange._get_lob(symbol)
        if lob is not None:
            orders = list(lob.history_log)[-length:]
        return [
            new_message(
                message_type=MessageType.QUERY_ORDER_STREAM,
                sender_id="Exchange",
                recipient_id=message.sender_id,
                send_time=now,
                recive_time=now,
                content={"symbol": symbol, "length": length, "orders": orders, "mkt_closed": not exchange.is_open},
            )
        ]
    if msg_type == MessageType.QUERY_TRANSACTED_VOLUME:
        symbol = message.content.get("symbol")
        if not isinstance(symbol, str):
            symbol = None
        lookback = message.content.get("lookback_period", "60s")
        try:
            td = (
                pd.Timedelta(lookback)
                if not isinstance(lookback, (int, float))
                else pd.Timedelta(seconds=float(lookback))
            )
        except Exception:
            td = pd.Timedelta(seconds=60)
        cutoff = now - td
        vol = 0
        lob = exchange._get_lob(symbol)
        if lob is not None:
            for t in lob.history_log:
                try:
                    ts = pd.to_datetime(t.get("timestamp"))
                    if ts >= cutoff:
                        vol += int(t.get("quantity", 0))
                except Exception:
                    pass
        return [
            new_message(
                message_type=MessageType.QUERY_TRANSACTED_VOLUME,
                sender_id="Exchange",
                recipient_id=message.sender_id,
                send_time=now,
                recive_time=now,
                content={"symbol": symbol, "transacted_volume": vol, "mkt_closed": not exchange.is_open},
            )
        ]
    if msg_type == MessageType.QUERY_FUNDAMENTAL:
        responses = []
        requests = message.content.get("requests") or []
        if not requests and message.content.get("symbol"):
            requests = [{"symbol": message.content.get("symbol") }]
        for req in requests:
            symbol = req.get("symbol") if isinstance(req, dict) else None
            mid_price = None
            lob = exchange._get_lob(symbol)
            if lob is not None:
                snap = lob.snapshot_top_n(1)
                bid = float(snap["buy"][0][0]) if snap.get("buy") else None
                ask = float(snap["sell"][0][0]) if snap.get("sell") else None
                if bid is not None and ask is not None:
                    mid_price = round((bid + ask) / 2.0, 2)
            responses.append(
                new_message(
                    message_type=MessageType.QUERY_FUNDAMENTAL,
                    sender_id="Exchange",
                    recipient_id=message.sender_id,
                    send_time=now,
                    recive_time=now,
                    content={"symbol": symbol, "data": mid_price, "mkt_closed": not exchange.is_open},
                )
            )
        return responses
    if msg_type == MessageType.QUERY_TOP_OF_BOOK:
        responses = []
        requests = message.content.get("requests") or []
        if not requests and message.content.get("symbol"):
            requests = [{"symbol": message.content.get("symbol"), "depth": message.content.get("depth", 1)}]
        for req in requests:
            symbol = req.get("symbol") if isinstance(req, dict) else None
            depth = int(req.get("depth", 1)) if isinstance(req, dict) else 1
            bids = []
            asks = []
            lob = exchange._get_lob(symbol)
            if lob is not None:
                snap = lob.snapshot_top_n(depth)
                bids = snap.get("buy", [])
                asks = snap.get("sell", [])
            best_bid = float(bids[0][0]) if bids else None
            best_ask = float(asks[0][0]) if asks else None
            responses.append(
                new_message(
                    message_type=MessageType.QUERY_TOP_OF_BOOK,
                    sender_id="Exchange",
                    recipient_id=message.sender_id,
                    send_time=now,
                    recive_time=now,
                    content={
                        "symbol": symbol,
                        "depth": depth,
                        "best_bid": best_bid,
                        "best_ask": best_ask,
                        "bids": bids,
                        "asks": asks,
                        "mkt_closed": not exchange.is_open,
                    },
                )
            )
        return responses
    return []


def _handle_market_data(exchange, message, now):
    content = message.content or {}
    responses = []
    if content.get("type") == "query_symbols":
        n = int(content.get("n", 3))
        universe = list(exchange.lob_dict.keys()) or ["SYM1", "SYM2", "SYM3", "SYM4"]
        if len(universe) < n:
            universe += [f"SYM{i}" for i in range(len(universe) + 1, n + 1)]
        selected = universe[:n]
        responses.append(
            new_message(
                message_type=MessageType.MKT_DATA,
                sender_id="Exchange",
                recipient_id=message.sender_id,
                send_time=now,
                recive_time=now,
                content={"symbols": selected},
            )
        )
    else:
        for req in content.get("requests", []):
            symbol = req.get("symbol", "SYM1")
            lob = exchange._get_lob(symbol)
            snap = lob.snapshot_top_n(1) if lob is not None else {"buy": [], "sell": []}
            best_bid = float(snap["buy"][0][0]) if snap["buy"] else None
            best_ask = float(snap["sell"][0][0]) if snap["sell"] else None
            mid = None
            if best_bid is not None and best_ask is not None:
                mid = round((best_bid + best_ask) / 2.0, 2)
            snapshot = {
                "symbol": symbol,
                "best_bid": best_bid,
                "best_ask": best_ask,
                "mid": mid,
                "ts": str(now),
            }
            responses.append(
                new_message(
                    message_type=MessageType.MKT_DATA,
                    sender_id="Exchange",
                    recipient_id=message.sender_id,
                    send_time=now,
                    recive_time=now,
                    content=snapshot,
                )
            )
    return responses
