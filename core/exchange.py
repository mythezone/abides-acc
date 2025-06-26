from core.lob import LimitOrderBook
from core.message import Message, MessageType
from core.order import Order
from core.symbol import Symbol
import pandas as pd


class Exchange:
    def __init__(self, symbols: dict[str, Symbol]):
        self.symbols = symbols
        self.lob_dict = {
            symbol_name: LimitOrderBook(symbol_name) for symbol_name in symbols
        }

    def handle_message(self, message: Message):
        response_messages = []
        for req in message.content.get("requests", []):
            msg_type = req.get("type")
            symbol = req.get("symbol")

            if msg_type in ("limit_order", "market_order"):
                order = Order.from_dict(req)
                trades = self.lob_dict[symbol].add_order(order)
                response_messages.append(
                    Message(
                        message_type=MessageType.ORDER_EXECUTED,
                        sender_id="Exchange",
                        recipient_id=order.agent_id,
                        send_time=message.send_time,
                        content={"trades": trades},
                    )
                )
            elif msg_type == "cancel_order":
                order_id = req.get("order_id")
                self.lob_dict[symbol].cancel_order(order_id)
                response_messages.append(
                    Message(
                        message_type=MessageType.ORDER_CANCELLED,
                        sender_id="Exchange",
                        recipient_id=message.sender_id,
                        send_time=message.send_time,
                        content={"order_id": order_id, "symbol": symbol},
                    )
                )
            elif msg_type == "query_kline":
                start_date = pd.to_datetime(req["start"])
                end_date = pd.to_datetime(req["end"])
                df = self.symbols[symbol].get_kline(start_date, end_date)
                response_messages.append(
                    Message(
                        message_type=MessageType.MKT_DATA,
                        sender_id="Exchange",
                        recipient_id=message.sender_id,
                        send_time=message.send_time,
                        content={"symbol": symbol, "kline": df.to_dict()},
                    )
                )
        return response_messages
