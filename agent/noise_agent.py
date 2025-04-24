from agent.trading_agent import TradingAgent
from core import message
from core.exchange import OrderBook
from order.limit_order import LimitOrder
from util.util import log_print
import random
from core.message import Message, MessageType as MT
from core.const import EXCHANGE_ID
from core.symbol import Symbol
from core.base import RandomState

from math import sqrt
import numpy as np
import pandas as pd

from typing import TYPE_CHECKING, Dict

if TYPE_CHECKING:
    from core.kernel import Kernel


class NoiseAgent(TradingAgent):

    def __init__(
        self,
        cash: int = 100000,
        kernel: "Kernel" = None,
        probability: float = 0.8,
        min_quantity: int = 10,
        max_quantity: int = 20,
        **kwargs
    ):

        # Base class init.
        super().__init__(id, cash=cash, kernel=kernel, **kwargs)

        self.probability = probability

        # The agent begins in its "complete" state, not waiting for
        # any special event or condition.
        # self.state = "AWAITING_WAKEUP"

        # The agent must track its previous wake time, so it knows how many time
        # units have passed.
        self.prev_wake_time = None
        self.random_state = RandomState().state
        self.min_quantity = min_quantity
        self.max_quantity = max_quantity

    def kernelStarting(self, startTime):
        # self.kernel is set in Agent.kernelInitializing()
        # self.exchangeID is set in TradingAgent.kernelStarting()

        super().kernelStarting(startTime)

        self.oracle = self.kernel.oracle

    def kernelStopping(self):
        # Always call parent method to be safe.
        super().kernelStopping()

        # Print end of day valuation.
        H = int(round(self.getHoldings(self.symbol), -2) / 100)

        # noise trader surplus is marked to EOD
        bid, bid_vol, ask, ask_vol = self.getKnownBidAsk(self.symbol)

        if bid and ask:
            rT = int(bid + ask) / 2
        else:
            rT = self.last_trade[self.symbol]

        # final (real) fundamental value times shares held.
        surplus = rT * H

        log_print("surplus after holdings: {}", surplus)

        # Add ending cash value and subtract starting cash value.
        surplus += self.holdings["CASH"] - self.starting_cash
        surplus = float(surplus) / self.starting_cash

        self.logEvent("FINAL_VALUATION", surplus, True)

        log_print(
            "{} final report.  Holdings {}, end cash {}, start cash {}, final fundamental {}, surplus {}",
            self.name,
            H,
            self.holdings["CASH"],
            self.starting_cash,
            rT,
            surplus,
        )

        print("Final relative surplus", self.name, surplus)

    def wakeup(self):

        self.state = "INACTIVE"

        if self.mkt_closed and (not self.symbol in self.daily_close_price):
            self.getCurrentSpread(self.symbol)
            self.state = "AWAITING_SPREAD"
            return

        if type(self) == NoiseAgent:
            self.getCurrentSpread(self.symbol)
            self.state = "AWAITING_SPREAD"
        else:
            self.state = "ACTIVE"

    def place_order(self):
        # place order in random direction at a mid
        delay = 0

        for symbol_name in Symbol._symbol_dict.keys():
            delay += self.order_delay()
            quantity = self.random_state.randint(self.min_quantity, self.max_quantity)
            is_buy_order = self.random_state.choice([True, False])
            msg = Message(
                message_type=MT.MKT_ORDER,
                sender_id=self.agent_id,
                recipient_id=EXCHANGE_ID,
                send_time=self.kernel.clock.now(),
                recive_time=self.kernel.clock.future(nanoseconds=delay),
            )
            if is_buy_order:
                best_price = OrderBook[symbol_name].get_best_price(side="bid")
            else:
                best_price = OrderBook[symbol_name].get_best_price(side="ask")

            if best_price is not None:
                msg.set_limit_order(symbol_name, quantity, is_buy_order, best_price[0])
                self.send(msg, recive_delay=self.distance_delay())

    def message_handler(self, currentTime, msg):
        # Parent class schedules market open wakeup call once market open/close times are known.
        super().message_handler(currentTime, msg)

        # We have been awakened by something other than our scheduled wakeup.
        # If our internal state indicates we were waiting for a particular event,
        # check if we can transition to a new state.

        if self.state == "AWAITING_SPREAD":
            # We were waiting to receive the current spread/book.  Since we don't currently
            # track timestamps on retained information, we rely on actually seeing a
            # QUERY_SPREAD response message.

            if msg.body["msg"] == "QUERY_SPREAD":
                # This is what we were waiting for.

                # But if the market is now closed, don't advance to placing orders.
                if self.mkt_closed:
                    return

                # We now have the information needed to place a limit order with the eta
                # strategic threshold parameter.
                self.placeOrder()
                self.state = "AWAITING_WAKEUP"

    # Internal state and logic specific to this agent subclass.

    # Cancel all open orders.
    # Return value: did we issue any cancellation requests?
    def cancelOrders(self):
        if not self.orders:
            return False

        for id, order in self.orders.items():
            self.cancelOrder(order)

        return True

    def getWakeFrequency(self):
        return pd.Timedelta(self.random_state.randint(low=0, high=100), unit="ns")
