from agent.trading_agent import TradingAgent
from util.util import log_print

from math import sqrt
import numpy as np
import pandas as pd

from typing import TYPE_CHECKING, Dict

if TYPE_CHECKING:
    from core.kernel import Kernel


class NoiseAgent(TradingAgent):

    def __init__(self, cash: int = 100000, kernel: "Kernel" = None, **kwargs):

        # Base class init.
        super().__init__(id, cash=cash, kernel=kernel, **kwargs)

        # self.wakeup_time = (wakeup_time,)

        # self.symbol = symbol_name  # symbol to trade

        # The agent uses this to track whether it has begun its strategy or is still
        # handling pre-market tasks.
        self.trading = False

        # The agent begins in its "complete" state, not waiting for
        # any special event or condition.
        # self.state = "AWAITING_WAKEUP"

        # The agent must track its previous wake time, so it knows how many time
        # units have passed.
        self.prev_wake_time = None

        self.size = np.random.randint(20, 50)

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

    def placeOrder(self):
        # place order in random direction at a mid
        buy_indicator = np.random.randint(0, 1 + 1)

        bid, bid_vol, ask, ask_vol = self.getKnownBidAsk(self.symbol)

        if buy_indicator and ask:
            self.placeLimitOrder(self.symbol, self.size, buy_indicator, ask)
        elif not buy_indicator and bid:
            self.placeLimitOrder(self.symbol, self.size, buy_indicator, bid)

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
