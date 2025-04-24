# The ExchangeAgent expects a numeric agent id, printable name, agent type, timestamp to open and close trading,
# a list of equity symbols for which it should create order books, a frequency at which to archive snapshots
# of its order books, a pipeline delay (in ns) for order activity, the exchange computation delay (in ns),
# the levels of order stream history to maintain per symbol (maintains all orders that led to the last N trades),
# whether to log all order activity to the agent log, and a random state object (already seeded) to use
# for stochasticity.

from math import log
from core.base import Singleton, Handler

from core.const import EXCHANGE_ID
from core.symbol import Symbol
from typing import TYPE_CHECKING
import pandas as pd
from core.orderbook import OrderBook
from core.message import Message, MessageType as MT
from core.symbol import Symbol
from core.logger import Logger

if TYPE_CHECKING:
    from core.kernel import Kernel


class Exchange(Handler, metaclass=Singleton):

    def __init__(
        self,
        mkt_open: pd.Timestamp,
        mkt_close: pd.Timestamp,
        *args,
        kernel: "Kernel" = None,
        pipeline_delay=40000,
        computation_delay=1,
        log_ohlc=True,
        log_lob=True,
        log_lob_level=5,
        log_freq="3s",
        **kwargs,
    ):

        self.kernel = kernel
        self.mkt_close = mkt_close
        self.mkt_open = mkt_open

        self.pipeline_delay = pipeline_delay
        self.computation_delay = computation_delay

        self.log_ohlc = log_ohlc
        self.log_lob = log_lob
        self.log_lob_level = log_lob_level
        self.log_freq = log_freq

        self.args = args
        for key, value in kwargs.items():
            setattr(self, key, value)

        self.logger = Logger()
        self.init_log_msg()

    def init_log_msg(self):
        if self.log_lob:
            lob_msg = Message(
                message_type=MT.LOG_LOB,
                sender_id=EXCHANGE_ID,
                recipient_id=EXCHANGE_ID,
                send_time=self.kernel.now(),
                recive_time=self.kernel.now(),
                content={
                    "level": self.log_lob_level,
                    "log_freq": self.log_freq,
                },
            )
            self.send(lob_msg, recive_delay=0)

        if self.log_ohlc:
            ohlc_msg = Message(
                message_type=MT.LOG_OHLC,
                sender_id=EXCHANGE_ID,
                recipient_id=EXCHANGE_ID,
                send_time=self.kernel.now(),
                recive_time=self.kernel.now(),
                content={"log_freq": self.log_freq},
            )
            self.send(ohlc_msg, recive_delay=0)

    def process_msg(self, msg: Message):
        handler = self.get_handler(self, msg.message_type)
        handler(msg)

    @Handler.register_handler(MT.MKT_ORDER)
    def handle_order_book(self, msg: Message):
        pass

    @Handler.register_handler(MT.LOG_LOB)
    def handle_log_lob(self, msg: Message):
        level = msg.content["level"]
        for symbol_name in Symbol._symbol_name_list:
            order_book = OrderBook[symbol_name]
            lob = order_book.report_lob(level=level)
            self.logger.lob_log(
                symbol_name=symbol_name,
                kernel_time=self.kernel.now(),
                level=level,
                lob=lob,
            )
        msg = self.update_log_msg(msg)
        self.send(msg, recive_delay=0)

    @Handler.register_handler(MT.LOG_OHLC)
    def handle_log_ohlc(self, msg: Message):
        for symbol_name in Symbol._symbol_name_list:
            order_book = OrderBook[symbol_name]
            ohlc = order_book.ohlc

            self.logger.ohlc_log(
                symbol_name=symbol_name,
                kernel_time=self.kernel.now(),
                open_=ohlc[symbol_name]["open"],
                high=ohlc[symbol_name]["high"],
                low=ohlc[symbol_name]["low"],
                close=ohlc[symbol_name]["close"],
                volume=ohlc[symbol_name]["volume"],
            )
            order_book.reset_ohlc()

        msg = self.update_log_msg(msg)
        self.send(msg, recive_delay=0)

    @staticmethod
    def update_log_msg(log_msg: Message):
        log_msg.send_time = log_msg.recive_time
        log_msg.recive_time += pd.Timedelta(log_msg.content["log_freq"])
        return log_msg

    def send(self, msg: Message, recive_delay=0):
        self.kernel.inbox.put(msg, recive_delay=recive_delay)

    # def receiveMessage(self, currentTime, msg):

    #     if msg.body["msg"] == "LIMIT_ORDER":
    #         order = msg.body["order"]
    #         log_print("{} received LIMIT_ORDER: {}", self.name, order)
    #         if order.symbol not in self.order_books:
    #             log_print("Limit Order discarded.  Unknown symbol: {}", order.symbol)
    #         else:
    #             # Hand the order to the order book for processing.
    #             self.order_books[order.symbol].handleLimitOrder(deepcopy(order))
    #             self.publishOrderBookData()
    #     elif msg.body["msg"] == "MARKET_ORDER":
    #         order = msg.body["order"]
    #         log_print("{} received MARKET_ORDER: {}", self.name, order)
    #         if order.symbol not in self.order_books:
    #             log_print("Market Order discarded.  Unknown symbol: {}", order.symbol)
    #         else:
    #             # Hand the market order to the order book for processing.
    #             self.order_books[order.symbol].handleMarketOrder(deepcopy(order))
    #             self.publishOrderBookData()
    #     elif msg.body["msg"] == "CANCEL_ORDER":
    #         # Note: this is somewhat open to abuse, as in theory agents could cancel other agents' orders.
    #         # An agent could also become confused if they receive a (partial) execution on an order they
    #         # then successfully cancel, but receive the cancel confirmation first.  Things to think about
    #         # for later...
    #         order = msg.body["order"]
    #         log_print("{} received CANCEL_ORDER: {}", self.name, order)
    #         if order.symbol not in self.order_books:
    #             log_print(
    #                 "Cancellation request discarded.  Unknown symbol: {}", order.symbol
    #             )
    #         else:
    #             # Hand the order to the order book for processing.
    #             self.order_books[order.symbol].cancelOrder(deepcopy(order))
    #             self.publishOrderBookData()
    #     elif msg.body["msg"] == "MODIFY_ORDER":
    #         # Replace an existing order with a modified order.  There could be some timing issues
    #         # here.  What if an order is partially executed, but the submitting agent has not
    #         # yet received the norification, and submits a modification to the quantity of the
    #         # (already partially executed) order?  I guess it is okay if we just think of this
    #         # as "delete and then add new" and make it the agent's problem if anything weird
    #         # happens.
    #         order = msg.body["order"]
    #         new_order = msg.body["new_order"]
    #         log_print(
    #             "{} received MODIFY_ORDER: {}, new order: {}".format(
    #                 self.name, order, new_order
    #             )
    #         )
    #         if order.symbol not in self.order_books:
    #             log_print(
    #                 "Modification request discarded.  Unknown symbol: {}".format(
    #                     order.symbol
    #                 )
    #             )
    #         else:
    #             self.order_books[order.symbol].modifyOrder(
    #                 deepcopy(order), deepcopy(new_order)
    #             )
    #             self.publishOrderBookData()

    #     def updateSubscriptionDict(self, msg, currentTime):
    #         # The subscription dict is a dictionary with the key = agent ID,
    #         # value = dict (key = symbol, value = list [levels (no of levels to recieve updates for),
    #         # frequency (min number of ns between messages), last agent update timestamp]
    #         # e.g. {101 : {'AAPL' : [1, 10, pd.Timestamp(10:00:00)}}
    #         if msg.body["msg"] == "MARKET_DATA_SUBSCRIPTION_REQUEST":
    #             agent_id, symbol, levels, freq = (
    #                 msg.body["sender"],
    #                 msg.body["symbol"],
    #                 msg.body["levels"],
    #                 msg.body["freq"],
    #             )
    #             self.subscription_dict[agent_id] = {symbol: [levels, freq, currentTime]}
    #         elif msg.body["msg"] == "MARKET_DATA_SUBSCRIPTION_CANCELLATION":
    #             agent_id, symbol = msg.body["sender"], msg.body["symbol"]
    #             del self.subscription_dict[agent_id][symbol]

    def publishOrderBookData(self):
        """
        The exchange agents sends an order book update to the agents using the subscription API if one of the following
        conditions are met:
        1) agent requests ALL order book updates (freq == 0)
        2) order book update timestamp > last time agent was updated AND the orderbook update time stamp is greater than
        the last agent update time stamp by a period more than that specified in the freq parameter.
        """
        for agent_id, params in self.subscription_dict.items():
            for symbol, values in params.items():
                levels, freq, last_agent_update = values[0], values[1], values[2]
                orderbook_last_update = self.order_books[symbol].last_update_ts
                if (freq == 0) or (
                    (orderbook_last_update > last_agent_update)
                    and ((orderbook_last_update - last_agent_update).delta >= freq)
                ):
                    self.sendMessage(
                        agent_id,
                        Message(
                            {
                                "msg": "MARKET_DATA",
                                "symbol": symbol,
                                "bids": self.order_books[symbol].getInsideBids(levels),
                                "asks": self.order_books[symbol].getInsideAsks(levels),
                                "last_transaction": self.order_books[symbol].last_trade,
                                "exchange_ts": self.currentTime,
                            }
                        ),
                    )
                    self.subscription_dict[agent_id][symbol][2] = orderbook_last_update

    @classmethod
    def register_handler(cls, message_type: MT):
        def handler(func):
            cls.message_handler[message_type] = func
            return func

        return handler
