from core.message import MessageType

from .manager import register_handler


@register_handler(MessageType.SIMULATION_START)
def handle(exchange, message, now):
    exchange.selector.initialize(now)
    return []
