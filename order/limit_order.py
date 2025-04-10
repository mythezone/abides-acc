# LimitOrder class, inherits from Order class, adds a limit price.  These are the
# Orders that typically go in an Exchange's OrderBook.

from order.base import Order
from core.kernel import Kernel
from agent.FinancialAgent import dollarize
from copy import deepcopy
import pandas as pd 
from agent.base import Agent
from functools import total_ordering

import sys

# Module level variable that can be changed by config files.
silent_mode = False

@total_ordering
class LimitOrder(Order):

    def __init__(self, 
                 agent_id:int|Agent, 
                 time_placed:pd.Timestamp, 
                 symbol:str, 
                 quantity:int, 
                 is_buy_order:bool, 
                 limit_price:int, 
                 order_id=None, 
                 tag=None
                 ):

        super().__init__(agent_id, time_placed, symbol, quantity, is_buy_order, order_id, tag=tag)

        # The limit price is the minimum price the agent will accept (for a sell order) or
        # the maximum price the agent will pay (for a buy order).
        self.limit_price: int = limit_price

        # Used for compare operations.
        self.compare_price: int = -limit_price if is_buy_order else limit_price

    def __str__(self):
        if silent_mode: return ''

        filled = ''
        if self.fill_price: filled = " (filled @ {})".format(dollarize(self.fill_price))

        # Until we make explicit market orders, we make a few assumptions that EXTREME prices on limit
        # orders are trying to represent a market order.  This only affects printing - they still hit
        # the order book like limit orders, which is wrong.
        return "(Agent {} @ {}{}) : {} {} {} @ {}{}".format(self.agent_id, Kernel.fmtTime(self.time_placed),f" [{self.tag}]" if self.tag is not None else "","BUY" if self.is_buy_order else "SELL", self.quantity,self.symbol,dollarize(self.limit_price) if abs(self.limit_price) < sys.maxsize else 'MKT', filled)

    def __repr__(self):
        if silent_mode: return ''
        return self.__str__()

    def __copy__(self):
        order = LimitOrder(self.agent_id, self.time_placed, self.symbol, self.quantity, self.is_buy_order,
                           self.limit_price,
                           order_id=self.order_id,
                           tag=self.tag)
        Order._order_ids.pop()  # remove duplicate agent ID
        order.fill_price = self.fill_price
        return order

    def __deepcopy__(self, memodict={}):
        # Deep copy instance attributes
        agent_id = deepcopy(self.agent_id, memodict)
        time_placed = deepcopy(self.time_placed, memodict)
        symbol = deepcopy(self.symbol, memodict)
        quantity = deepcopy(self.quantity, memodict)
        is_buy_order = deepcopy(self.is_buy_order, memodict)
        limit_price = deepcopy(self.limit_price, memodict)
        order_id = deepcopy(self.order_id, memodict)
        tag = deepcopy(self.tag, memodict)
        fill_price = deepcopy(self.fill_price, memodict)

        # Create new order object
        order = LimitOrder(agent_id, time_placed, symbol, quantity, is_buy_order, limit_price,
                           order_id=order_id, tag=tag)
        order.fill_price = fill_price

        return order
    
    def __eq__(self, other):
        if not isinstance(other, LimitOrder):
            return False
        return self.id == other.id 
    
    def __lt__(self, other):
        # Compare LimitOrders based on their limit price
        if not isinstance(other, LimitOrder):
            return NotImplemented
        
        if self.compare_price == other.compare_price:
            return self.time_placed < other.time_placed
        return self.compare_price < other.compare_price
    


        
