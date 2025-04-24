# Basic class for an order book for one symbol, in the style of the major US Stock Exchanges.
# List of bid prices (index zero is best bid), each with a list of LimitOrders.
# List of ask prices (index zero is best ask), each with a list of LimitOrders.
import sys

from core.message import Message
from order.limit_order import LimitOrder
from util.util import log_print, be_silent

from copy import deepcopy
import pandas as pd
from pandas import json_normalize
from functools import reduce
from scipy.sparse import dok_matrix
from tqdm import tqdm


# from queue import PriorityQueue

from order.base import Order, Transaction
from order.limit_order import LimitOrder, OrderHeap
from core.symbol import Symbol


class OrderBook:
    _order_books = {}

    # An OrderBook requires an owning agent object, which it will use to send messages
    # outbound via the simulator Kernel (notifications of order creation, rejection,
    # cancellation, execution, etc).
    def __init__(self, symbol_name: str):
        # self.owner = owner
        if symbol_name in OrderBook._order_books:
            return
        self.symbol = Symbol[symbol_name]

        self.bid_side = OrderHeap(side="bid")
        self.ask_side = OrderHeap(side="ask")

        self.last_trade = None

        # Create an empty list of dictionaries to log the full order book depth (price and volume) each time it changes.
        self.book_log = []
        self.quotes_seen = set()
        self.ohlc = {
            "open": None,
            "high": None,
            "low": None,
            "close": None,
            "volume": 0,
        }

        # Last timestamp the orderbook for that symbol was updated
        self.last_update_ts = None
        OrderBook._order_books[symbol_name] = self

    def handle_limit_order(self, order: LimitOrder):
        # 获取己方订单簿信息
        this_book = self.bid_side if order.is_buy_order else self.ask_side

        if this_book.empty() or (
            order.is_buy_order and order.compare_price >= this_book.peek().compare_price
        ):
            this_book.put(order)
            return
        # 获取对手盘信息
        that_book = self.ask_side if order.is_buy_order else self.bid_side
        if that_book.empty():
            this_book.put(order)
            return

        matching = True

        while matching and that_book:
            if order.is_buy_order and order.limit_price < that_book.peek().limit_price:
                self.ask_side.put(order)
                return
            elif (
                not order.is_buy_order
                and order.limit_price > that_book.peek().limit_price
            ):
                self.bid_side.put(order)
                return
            best_order = that_book.peek()

            trade_quantity = min(order.quantity, best_order.quantity)

            trade_price = best_order.limit_price
            transaction_time = self.owner.currentTime

            transaction = Transaction(
                time=transaction_time,
                price=trade_price,
                quantity=trade_quantity,
                bid_order_id=order.id if order.is_buy_order else best_order.id,
                ask_order_id=best_order.id if order.is_buy_order else order.id,
            )

            order.deal(transaction)
            best_order.deal(transaction)
            if best_order.remaining_quantity == 0:
                # 如果对手盘的订单完全成交，从订单簿中删除该订单
                that_book.get()

            if that_book.empty():
                # 如果对手盘被吃空，直接将剩余的量放入订单簿
                this_book.put(order)
                matching = False

            if order.remaining_quantity == 0:
                # 如果己方订单完全成交，直接返回
                matching = False

    def handle_market_order(self, order: Order):

        # 匹配市价单，直到订单完全成交或对手盘耗尽
        book = self.ask_side if order.is_buy_order else self.bid_side
        matching = True

        while matching and book:
            best_order = book.peek()
            # 交易量以双方较小的量为准
            trade_quantity = min(order.quantity, best_order.quantity)
            # 交易价格以对手盘的价格为准
            trade_price = best_order.limit_price
            # 这个时间待更新
            transaction_time = self.owner.currentTime

            transaction = Transaction(
                time=transaction_time,
                price=trade_price,
                quantity=trade_quantity,
                bid_order_id=order.id if order.is_buy_order else best_order.id,
                ask_order_id=best_order.id if order.is_buy_order else order.id,
            )

            order.deal(transaction)
            best_order.deal(transaction)

            if best_order.remaining_quantity == 0:
                # 如果对手盘的订单完全成交，从订单簿中删除该订单
                book.get()

            # 目前的策略是当对手盘被吃空就直接取消剩余的量
            if book.empty():
                matching = False

            if order.remaining_quantity == 0:
                matching = False

    def cancel_order(self, order: Order):
        book = self.bid_side if order.is_buy_order else self.ask_side
        if not book:
            return

        book.get_by_id(order.order_id)
        order.cancel()

    def modify_order(self, order: LimitOrder, modifier: Transaction):
        book = self.bid_side if order.is_buy_order else self.ask_side
        if not book:
            return

        order.modify(modifier)

    def get_current_spread(self, level=1):
        ask_side_level = self.ask_side.get_price_level(level)
        bid_side_level = self.bid_side.get_price_level(level)
        min_len = min(len(ask_side_level), len(bid_side_level))
        ask_side_level = ask_side_level[:min_len]
        bid_side_level = bid_side_level[:min_len]
        result = [a - b for a, b in zip(ask_side_level, bid_side_level)]
        return result

    def book_log_to_df(self):
        """Returns a pandas DataFrame constructed from the order book log, to be consumed by
            agent.ExchangeAgent.logOrderbookSnapshots.

            The first column of the DataFrame is `QuoteTime`. The succeeding columns are prices quoted during the
            simulation (as taken from self.quotes_seen).

            Each row is a snapshot at a specific time instance. If there is volume at a certain price level (negative
            for bids, positive for asks) this volume is written in the column corresponding to the price level. If there
            is no volume at a given price level, the corresponding column has a `0`.

            The data is stored in a sparse format, such that a value of `0` takes up no space.

        :return:
        """
        pass

    def reset_ohlc(self):
        """Resets the OHLC data for the order book."""
        self.ohlc = {
            "open": self.ohlc["close"],
            "high": self.ohlc["close"],
            "low": self.ohlc["close"],
            "close": self.ohlc["close"],
            "volume": 0,
        }

    def report_lob(self, level: int = 5):
        # Get the bid and ask prices and volumes
        bid_book = self.bid_side.get_book(level)
        ask_book = self.ask_side.get_book(level)

        # Create a DataFrame with the bid and ask prices and volumes
        res = ""
        for i in range(level):
            res += f"{ask_book[i][0]},"
        for i in range(level):
            res += f"{ask_book[i][1]},"
        for i in range(level):
            res += f"{bid_book[i][0]},"
        for i in range(level):
            if i == level - 1:
                res += f"{bid_book[i][1]}"
            else:
                res += f"{bid_book[i][1]},"
        return res

    # Print a nicely-formatted view of the current order book.
    # def prettyPrint(self, silent=False):
    #     # Start at the highest ask price and move down.  Then switch to the highest bid price and move down.
    #     # Show the total volume at each price.  If silent is True, return the accumulated string and print nothing.

    #     # If the global silent flag is set, skip prettyPrinting entirely, as it takes a LOT of time.
    #     if be_silent:
    #         return ""

    #     book = "{} order book as of {}\n".format(self.symbol, self.owner.currentTime)
    #     book += "Last trades: simulated {:d}, historical {:d}\n".format(
    #         self.last_trade,
    #         self.owner.oracle.observePrice(
    #             self.symbol,
    #             self.owner.currentTime,
    #             sigma_n=0,
    #             random_state=self.owner.random_state,
    #         ),
    #     )

    #     book += "{:10s}{:10s}{:10s}\n".format("BID", "PRICE", "ASK")
    #     book += "{:10s}{:10s}{:10s}\n".format("---", "-----", "---")

    #     for quote, volume in self.getInsideAsks()[-1::-1]:
    #         book += "{:10s}{:10s}{:10s}\n".format(
    #             "", "{:d}".format(quote), "{:d}".format(volume)
    #         )

    #     for quote, volume in self.getInsideBids():
    #         book += "{:10s}{:10s}{:10s}\n".format(
    #             "{:d}".format(volume), "{:d}".format(quote), ""
    #         )

    #     if silent:
    #         return book

    #     log_print(book)

    @classmethod
    def get(cls, symbol_name: str):
        orderbook = cls._order_books.get(symbol_name, None)
        if not orderbook:
            orderbook = OrderBook(symbol_name)
        return orderbook

    @classmethod
    def __class_getitem__(cls, symbol_name: str):
        return cls.get(symbol_name)

    def get_best_price(self, side: str = "ask"):
        if side == "ask":
            return self.ask_side.get_price_level(1)
        else:
            return self.bid_side.get_price_level(1)
