from core.message import MessageType, new_message

from .manager import register_handler


@register_handler(MessageType.SELECT_SYMBOLS_REQUEST)
def handle(exchange, message, now):
    params = message.content or {}
    selection = exchange.selector.sample(params, now)
    return [
        new_message(
            message_type=MessageType.SELECT_SYMBOLS_RESPONSE,
            sender_id="Exchange",
            recipient_id=message.sender_id,
            send_time=now,
            recive_time=now,
            content={
                "strategy": params.get("strategy", "random"),
                "stocks": selection,
                "count": len(selection),
            },
        )
    ]
