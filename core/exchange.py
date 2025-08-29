from core.lob import LimitOrderBook
from core.message import MessageType, new_message, Message
from core.order import Order, LimitOrder, MarketOrder
import pandas as pd
import numpy as np


class Exchange:
    def __init__(self, symbols: dict):
        self.symbols = symbols
        self.lob_dict = {
            symbol_name: LimitOrderBook(symbol_name) for symbol_name in symbols
        }

    def handle_message(self, message: Message):
        response_messages = []
        now = message.send_time

        if message.message_type in (MessageType.LMT_ORDER, MessageType.MKT_ORDER, MessageType.SUBMIT_ORDER):
            # Accept generic SUBMIT_ORDER and type-specific LMT/MKT
            for req in message.content.get("requests", []):
                symbol = req.get("symbol", "SYM")
                # Ensure a LOB exists even if symbols were not pre-registered
                if symbol not in self.lob_dict:
                    self.lob_dict[symbol] = LimitOrderBook(symbol)

                # Decide order class
                otype = req.get("type")
                if otype == "limit_order":
                    order = LimitOrder.from_dict(req)
                elif otype == "market_order":
                    order = MarketOrder.from_dict(req)
                else:
                    order = Order.from_dict(req)

                trades = self.lob_dict[symbol].add_order(order)

                # Acknowledge
                response_messages.append(
                    new_message(
                        message_type=MessageType.ORDER_ACCEPTED,
                        sender_id="Exchange",
                        recipient_id=order.agent_id,
                        send_time=now,
                        recive_time=now,
                        content={"order_id": order.id, "symbol": symbol},
                    )
                )
                # Execution report (may be empty)
                if trades:
                    response_messages.append(
                        new_message(
                            message_type=MessageType.ORDER_EXECUTED,
                            sender_id="Exchange",
                            recipient_id=order.agent_id,
                            send_time=now,
                            recive_time=now,
                            content={"trades": trades, "symbol": symbol},
                        )
                    )
        elif message.message_type == MessageType.CANCEL_ORDER:
            for req in message.content.get("requests", []):
                symbol = req.get("symbol")
                order_id = req.get("order_id")
                self.lob_dict[symbol].cancel_order(order_id)
                response_messages.append(
                    new_message(
                        message_type=MessageType.ORDER_CANCELLED,
                        sender_id="Exchange",
                        recipient_id=message.sender_id,
                        send_time=now,
                        recive_time=now,
                        content={"order_id": order_id, "symbol": symbol},
                    )
                )
        elif message.message_type == MessageType.MKT_DATA:
            content = message.content or {}
            if content.get("type") == "query_symbols":
                n = int(content.get("n", 3))
                # Provide dummy symbol list
                universe = list(self.lob_dict.keys()) or ["SYM1", "SYM2", "SYM3", "SYM4"]
                if len(universe) < n:
                    # Pad with synthetic symbols
                    universe += [f"SYM{i}" for i in range(len(universe) + 1, n + 1)]
                selected = universe[:n]
                response_messages.append(
                    new_message(
                        message_type=MessageType.MKT_DATA,
                        sender_id="Exchange",
                        recipient_id=message.sender_id,
                        send_time=now,
                        recive_time=now,
                        content={"symbols": selected},
                    )
                )
            else:
                for req in content.get("requests", []):
                    symbol = req.get("symbol", "SYM1")
                    # Return a dummy snapshot
                    best_bid = round(np.random.uniform(10, 100), 2)
                    best_ask = round(best_bid + np.random.uniform(0.01, 0.5), 2)
                    snapshot = {
                        "symbol": symbol,
                        "best_bid": best_bid,
                        "best_ask": best_ask,
                        "mid": round((best_bid + best_ask) / 2, 2),
                        "ts": str(now),
                    }
                    response_messages.append(
                        new_message(
                            message_type=MessageType.MKT_DATA,
                            sender_id="Exchange",
                            recipient_id=message.sender_id,
                            send_time=now,
                            recive_time=now,
                            content=snapshot,
                        )
                    )
        return response_messages
