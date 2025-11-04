import pandas as pd

from core.message import MessageType, new_message

from .manager import register_handler


@register_handler(MessageType.MKT_DATA_SUBSCRIPTION_TICK)
def handle(exchange, message, now):
    aid = message.content.get("agent_id")
    symbol = message.content.get("symbol")
    sub = exchange._subs.get(aid, {}).get(symbol) if aid else None
    if not sub:
        return []
    lob = exchange._get_lob(symbol)
    depth = int(sub.get("depth", 1))
    freq_ms = int(sub.get("freq_ms", 1000))
    snap = lob.snapshot_top_n(depth) if lob is not None else {"buy": [], "sell": []}
    payload = {
        "symbol": symbol,
        "depth": depth,
        "bids": snap.get("buy", []),
        "asks": snap.get("sell", []),
        "ts": str(now),
    }
    msg = new_message(
        message_type=MessageType.MKT_DATA,
        sender_id="Exchange",
        recipient_id=aid,
        send_time=now,
        recive_time=now,
        content=payload,
    )
    exchange._emit(msg)
    sub["last_sent"] = now
    next_time = now + pd.Timedelta(milliseconds=freq_ms)
    exchange._schedule_subscription_tick(aid, symbol, next_time)
    return []
