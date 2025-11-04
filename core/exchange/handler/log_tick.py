from core.message import MessageType

from .manager import register_handler


@register_handler(MessageType.LOG_TICK)
def handle(exchange, message, now):
    try:
        exchange._tick_log(now)
    except Exception:
        pass
    return []
