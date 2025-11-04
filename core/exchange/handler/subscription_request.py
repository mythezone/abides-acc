import pandas as pd

from core.message import MessageType, new_message

from .manager import register_handler


@register_handler(MessageType.MKT_DATA_SUBSCRIPTION_REQUEST)
def handle(exchange, message, now):
    subs = message.content.get("subscriptions") or []
    aid = message.sender_id
    cur = exchange._subs.setdefault(aid, {})
    for s in subs:
        sym = s.get("symbol")
        if sym is None:
            continue
        freq_ms = int(s.get("freq_ms", 1000))
        cur[sym] = {
            "depth": int(s.get("depth", 1)),
            "freq_ms": freq_ms,
            "last_sent": None,
        }
        exchange._schedule_subscription_tick(
            aid,
            sym,
            now + pd.Timedelta(milliseconds=freq_ms),
        )
        depth = int(s.get("depth", 1))
        lob = exchange._get_lob(sym)
        snap = lob.snapshot_top_n(depth) if lob is not None else {"buy": [], "sell": []}
        payload = {
            "symbol": sym,
            "depth": depth,
            "bids": snap.get("buy", []),
            "asks": snap.get("sell", []),
            "ts": str(now),
        }
        exchange._emit(
            new_message(
                message_type=MessageType.MKT_DATA,
                sender_id="Exchange",
                recipient_id=aid,
                send_time=now,
                recive_time=now,
                content=payload,
            )
        )
        cur[sym]["last_sent"] = now

    return [
        new_message(
            message_type=MessageType.MKT_DATA_SUBSCRIPTION_REQUEST,
            sender_id="Exchange",
            recipient_id=message.sender_id,
            send_time=now,
            recive_time=now,
            content={"status": "ok", "size": len(subs)},
        )
    ]
