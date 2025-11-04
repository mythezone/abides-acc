from core.message import MessageType

from .manager import register_handler


@register_handler(MessageType.MKT_OPEN, MessageType.MKT_CLOSE)
def handle(exchange, message, now):
    exchange.is_open = message.message_type == MessageType.MKT_OPEN
    if exchange.logger is not None:
        exchange.logger.exchange_log(
            f"Market {'OPEN' if exchange.is_open else 'CLOSE'}",
            kernel_time=now,
            type_="SESSION",
        )
    return []
