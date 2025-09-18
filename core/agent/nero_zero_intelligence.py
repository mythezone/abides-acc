from core.agent.fundamental import FundamentalTrackingAgent
from core.message import MessageType, MessageQueue, Message, new_message
from typing import List, Optional

import numpy as np
import pandas as pd


class NearZeroIntelligenceAgent(FundamentalTrackingAgent):
    """TO DO: get fundamental value."""
    def __init__(
        self,
        id,
        message_queue: MessageQueue = None,
        initial_symbols: Optional[List[str]] = None,
        alpha=0.85,
        kappa=4.10,
        phi=0.016,
        period_limit=5,
        *args,
        **kwargs,
    ):
        super().__init__(
            id,
            *args,
            message_queue=message_queue,
            initial_symbols=initial_symbols,
            **kwargs,
        )
        self.subscribed_symbols: List[str] = (initial_symbols or [])[:]
        self.selected_symbols = list(
            np.random.choice(
                self.subscribed_symbols, int(np.random.randint(1, 3)), replace=False
            )
        )
        self.alpha = alpha
        self.kappa = kappa
        self.phi = phi
        self.period_limit = period_limit

        self.current_period = 0
        self.prev_avg_price = 0
        self.period_trades = []

    def action(self):
        super().action()

        for symbol in self.selected_symbols:
            requests = []

            # make the trading decision
            is_buyer = self._determine_buyer_rule(symbol=symbol)

            # get fundamental values
            fundamental_value = self._get_fundamental_price()

            # get transaction price
            price = self._generate_price(
                is_buyer=is_buyer, fundamental_value=fundamental_value
            )

            # generate size
            # Since the paper doesn't speicfy how to generate ORDER SIZE, here I just follow the implementation in ZeroIntellugenceAgent.
            inventory = int(self.portfolio.holdings.get(symbol, 0))
            quantity = int(np.random.randint(1, 50))
            if not is_buyer and inventory > 0:
                quantity = max(1, min(quantity, inventory))

            # add content to contents
            order = {
                "type": "limit_order",
                "symbol": symbol,
                "agent_id": self.id,
                "timestamp": str(self.current_time),
                "side": "buy" if is_buyer else "sell",
                "quantity": quantity,
                "price": price,
            }
            requests.append(order)

        # when the for loop ends, submit the orders once
        if requests:
            msg = new_message(
                message_type=MessageType.SUBMIT_ORDER,
                sender_id=self.id,
                recipient_id="Exchange",
                send_time=self.current_time,
                recive_time=self.current_time,
                content={"requests": requests},
            )
            self.send(msg)

        # self.current_period increment
        self.current_period += 1
        if self.current_period > self.period_limit:
            self._end_period()

    def _determine_buyer_rule(self, symbol) -> bool:
        """Return true if it is a buyer."""
        p = np.random.rand()
        pi_t = np.max(0.5 - self.phi * self.current_period, 0)
        is_buyer = p < pi_t
        # check if we have the current stock
        inventory = int(self.portfolio.holdings.get(symbol, 0))
        if not is_buyer and inventory == 0:
            is_buyer = True
        return is_buyer

    def _get_fundamental_price(self):
        """Return the current fundamental prices."""
        pass

    def _generate_price(self, is_buyer: bool, fundamental_value):
        """Generate the market price, based on fundamental value."""
        u = np.random.uniform(0, self.kappa * fundamental_value)  # random component
        price = (1 - self.alpha) * u + self.alpha * self.prev_avg_price

        if is_buyer:
            price = np.min([price, self.portfolio.cash])
        return np.round(price, 2)

    def _end_period(self):
        if self.period_trades:
            # calculate trading quantity via weighted average price
            total_value = 0
            total_quantity = 0
            for symbol in self.selected_symbols:
                period_trades_for_symbol = [
                    trade[symbol] for trade in self.period_trades if symbol in trade
                ]
                total_value = np.sum(
                    price * qty for price, qty in period_trades_for_symbol
                )
                total_quantity = np.sum(qty for _, qty in period_trades_for_symbol)
            avg_price = total_value / total_quantity

        self.prev_avg_price = avg_price
        self.current_period = 0
        self.period_trades = []

    def process_inbox(self):
        """Here I just simply copy the implementation in ZeroIntelligenceAgent. I guess it's OK."""
        # First apply base processing (portfolio updates)
        super().process_inbox()
        # Then pick up symbol list if provided
        new_symbols = []
        keep = []
        for m in self.inbox:
            if m.message_type == MessageType.MKT_DATA and isinstance(m.content, dict):
                if "symbols" in m.content:
                    new_symbols.extend(m.content.get("symbols", []))
            elif m.message_type == MessageType.ORACLE_RESPONSE_LOB and isinstance(
                m.content, dict
            ):
                data = m.content.get("lob")
                symbol = m.content.get("symbol")
                # build simple heuristic orders near oracle best levels
                reqs = []
                try:
                    # Columns are: kernel_time, AskPrice0..AskVolume..BidPrice..BidVolume..
                    best_ask = None
                    best_bid = None
                    # Find first non-empty ask/bid price columns
                    for k in data.keys():
                        if str(k).startswith("AskPrice0") or str(k) == "AskPrice0":
                            val = data[k]
                            if pd.notna(val) and val != "":
                                best_ask = float(val)
                                break
                    for k in data.keys():
                        if str(k).startswith("BidPrice0") or str(k) == "BidPrice0":
                            val = data[k]
                            if pd.notna(val) and val != "":
                                best_bid = float(val)
                                break
                    if best_ask is not None and best_bid is not None:
                        mid = round((best_ask + best_bid) / 2.0, 2)
                        # Place small aggressive orders around oracle implied levels
                        # buy leg
                        reqs.append(
                            {
                                "type": "limit_order",
                                "symbol": symbol,
                                "agent_id": self.id,
                                "timestamp": str(self.current_time),
                                "side": "buy",
                                "quantity": int(np.random.randint(1, 50)),
                                "price": best_bid,
                            }
                        )
                        # sell leg only if inventory is available
                        inv = int(self.portfolio.holdings.get(symbol, 0))
                        if inv > 0:
                            qty = max(1, min(int(np.random.randint(1, 50)), inv))
                            reqs.append(
                                {
                                    "type": "limit_order",
                                    "symbol": symbol,
                                    "agent_id": self.id,
                                    "timestamp": str(self.current_time),
                                    "side": "sell",
                                    "quantity": qty,
                                    "price": best_ask,
                                }
                            )
                        # mid buy
                        reqs.append(
                            {
                                "type": "limit_order",
                                "symbol": symbol,
                                "agent_id": self.id,
                                "timestamp": str(self.current_time),
                                "side": "buy",
                                "quantity": int(np.random.randint(1, 20)),
                                "price": mid,
                            }
                        )
                except Exception:
                    pass
                if reqs:
                    msg = new_message(
                        message_type=MessageType.SUBMIT_ORDER,
                        sender_id=self.id,
                        recipient_id="Exchange",
                        send_time=self.current_time,
                        recive_time=self.current_time,
                        content={"requests": reqs},
                    )
                    self.send(msg)
            elif m.message_type == MessageType.ORACLE_RESPONSE_OHLC and isinstance(
                m.content, dict
            ):
                data = m.content.get("ohlc") or {}
                symbol = m.content.get("symbol")
                reqs = []
                try:
                    close = data.get("close") or data.get("close")
                    if close is not None and close != "":
                        close = float(close)
                        # place buy/sell around close
                        reqs.append(
                            {
                                "type": "limit_order",
                                "symbol": symbol,
                                "agent_id": self.id,
                                "timestamp": str(self.current_time),
                                "side": "buy",
                                "quantity": int(np.random.randint(1, 50)),
                                "price": close,
                            }
                        )
                        inv = int(self.portfolio.holdings.get(symbol, 0))
                        if inv > 0:
                            qty = max(1, min(int(np.random.randint(1, 50)), inv))
                            reqs.append(
                                {
                                    "type": "limit_order",
                                    "symbol": symbol,
                                    "agent_id": self.id,
                                    "timestamp": str(self.current_time),
                                    "side": "sell",
                                    "quantity": qty,
                                    "price": close,
                                }
                            )
                except Exception:
                    pass
                if reqs:
                    msg = new_message(
                        message_type=MessageType.SUBMIT_ORDER,
                        sender_id=self.id,
                        recipient_id="Exchange",
                        send_time=self.current_time,
                        recive_time=self.current_time,
                        content={"requests": reqs},
                    )
                    self.send(msg)
            else:
                keep.append(m)
        self.inbox = keep
        if new_symbols:
            # Deduplicate
            uniq = list(dict.fromkeys(new_symbols))
            self.subscribed_symbols = uniq

    def receive(self, message: Message):
        super().receive(message)
        if message.message_type == "ORDER_EXECUTED":
            symbol = str(message.content.get("symbol"))
            price = float(message.content.get("price"))
            size = int(message.content.get("size"))
            self.period_trades.append({symbol: (price, size)})
