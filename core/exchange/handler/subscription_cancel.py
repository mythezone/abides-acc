from core.message import MessageType, new_message

from .manager import register_handler


@register_handler(MessageType.MKT_DATA_SUBSCRIPTION_CANCELLATION)
def handle(exchange, message, now):
    aid = message.sender_id
    syms = message.content.get("symbols") or []
    if aid in exchange._subs:
        if syms:
            for s in syms:
                exchange._subs[aid].pop(s, None)
        else:
            exchange._subs.pop(aid, None)
    return [
        new_message(
            message_type=MessageType.MKT_DATA_SUBSCRIPTION_CANCELLATION,
            sender_id="Exchange",
            recipient_id=aid,
            send_time=now,
            recive_time=now,
            content={"status": "ok"},
        )
    ]
