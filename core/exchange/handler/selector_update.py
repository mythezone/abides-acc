from core.message import MessageType

from .manager import register_handler


@register_handler(MessageType.STOCK_SELECTOR_UPDATE)
def handle(exchange, message, now):
    exchange.selector.handle_update_message(now)
    return []
