from core.message import MessageType
from core.order import LimitOrder, MarketOrder, Order

from .manager import register_handler


@register_handler(MessageType.LMT_ORDER, MessageType.MKT_ORDER, MessageType.SUBMIT_ORDER)
def handle(exchange, message, now):
    for req in message.content.get("requests", []):
        stock = req.get("stock", "SYM")
        exchange._ensure_lob(stock)

        otype = req.get("type")
        if otype == "limit_order":
            if req.get("price") is None:
                order = MarketOrder.from_dict(req)
            else:
                order = LimitOrder.from_dict(req)
        elif otype == "market_order":
            order = MarketOrder.from_dict(req)
        else:
            order = Order.from_dict(req)

        try:
            setattr(order, "_stock", stock)
            sender_lower = str(message.sender_id).lower()
            if sender_lower.startswith("background_"):
                setattr(order, "_exempt_t1", True)
        except Exception:
            pass

        if not exchange._validate_order(order, now):
            continue
        if exchange._route_preopen(order, now):
            continue

        if exchange.workers > 0:
            shard = hash(stock) % exchange.workers
            exchange._worker_queues[shard].put((now, order))
        else:
            exchange._process_order(now, order)
    return []
