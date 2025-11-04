from core.message import MessageType, new_message

from .manager import register_handler


@register_handler(MessageType.CANCEL_ORDER)
def handle(exchange, message, now):
    responses = []
    for req in message.content.get("requests", []):
        symbol_val = req.get("symbol")
        if not isinstance(symbol_val, str):
            continue
        symbol = symbol_val
        lob = exchange.lob_dict.get(symbol)
        if lob is None:
            continue
        order_id = req.get("order_id")
        if order_id is not None:
            lob.cancel_order(order_id)
            responses.append(
                new_message(
                    message_type=MessageType.ORDER_CANCELLED,
                    sender_id="Exchange",
                    recipient_id=message.sender_id,
                    send_time=now,
                    recive_time=now,
                    content={"order_id": order_id, "symbol": symbol},
                )
            )
            continue

        side = req.get("side")
        price = req.get("price")
        quantity = req.get("quantity")
        if side not in ("buy", "sell"):
            continue
        try:
            price_val = float(price)
            qty_val = int(quantity)
        except Exception:
            continue
        removed = lob.cancel_by_price(side, price_val, qty_val)
        if removed <= 0:
            continue
        responses.append(
            new_message(
                message_type=MessageType.ORDER_CANCELLED,
                sender_id="Exchange",
                recipient_id=message.sender_id,
                send_time=now,
                recive_time=now,
                content={
                    "symbol": symbol,
                    "side": side,
                    "price": price_val,
                    "quantity": removed,
                    "mode": "price",
                },
            )
        )
    return responses
