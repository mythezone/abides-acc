# A basic Order type used by an Exchange to conduct trades or maintain an order book.
# This should not be confused with order Messages agents send to request an Order.
# Specific order types will inherit from this (like LimitOrder).

from copy import deepcopy
from agent.Agent import Agent

import pandas as pd 
import numpy as np 
from typing import Dict, List 

from util.base import Trackable

class Order(Trackable):
    # _order_id = 0
    # _order_ids = set()

    def __init__(self, agent:Agent|str, time_placed:pd.Timestamp, symbol:str, quantity:int, is_buy_order:bool, tag:Dict={}):
        # Agent ID: either the agent object or its ID.
        super().__init__()
        

        if isinstance(agent, Agent):
            self.agent = agent.id
        elif isinstance(agent, str):
            self.agent = Agent.get_agent_by_id(agent)

        # Time at which the order was created by the agent.
        self.time_placed = time_placed
        self.symbol = symbol
        self.quantity = quantity
        self.is_buy_order = is_buy_order

        # Create placeholder fields that don't get filled in until certain
        # events happen.  (We could instead subclass to a special FilledOrder
        # class that adds these later?)
        self.fill_price = None

        # Tag: a free-form user-defined field that can contain any information relevant to the
        #      entity placing the order.  Recommend keeping it alphanumeric rather than
        #      shoving in objects, as it will be there taking memory for the lifetime of the
        #      order and in all logging mechanisms.  Intent: for strategy agents to set tags
        #      to help keep track of the intent of particular orders, to simplify their code.
        self.tag = tag

    def to_dict(self):
        as_dict = deepcopy(self).__dict__
        as_dict['time_placed'] = self.time_placed.isoformat()
        return as_dict

    def __copy__(self):
        raise NotImplementedError

    def __deepcopy__(self, memodict={}):
        raise NotImplementedError
