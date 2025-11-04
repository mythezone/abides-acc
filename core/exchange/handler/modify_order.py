from core.message import MessageType, new_message
from core.order import LimitOrder, MarketOrder, Order

from .manager import register_handler


@register_handler(MessageType.MODIFY_ORDER)
def handle(exchange, message, now):
    responses = []
    for req in message.content.get("requests", []):
        symbol_val = req.get("symbol")
        if not isinstance(symbol_val, str):
            continue
        symbol = symbol_val
        order_id = req.get("order_id")
        new_order_dict = req.get("new_order", {})
        if symbol not in exchange.lob_dict:
            continue
        try:
            exchange.lob_dict[symbol].cancel_order(order_id)
        except Exception:
            pass
        responses.append(
            new_message(
                message_type=MessageType.ORDER_CANCELLED,
                sender_id="Exchange",
                recipient_id=message.sender_id,
                send_time=now,
                recive_time=now,
                content={"order_id": order_id, "symbol": symbol, "reason": "MODIFY"},
            )
        )
        otype = new_order_dict.get("type")
        if otype == "limit_order":
            order = LimitOrder.from_dict(new_order_dict)
        elif otype == "market_order":
            order = MarketOrder.from_dict(new_order_dict)
        else:
            order = Order.from_dict(new_order_dict)
        setattr(order, "_symbol", symbol)
        if exchange.workers > 0:
            shard = hash(symbol) % exchange.workers
            exchange._worker_queues[shard].put((now, order))
        else:
            exchange._process_order(now, order)
    return responses
