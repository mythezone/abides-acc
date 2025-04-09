from enum import Enum, unique
from agent.Agent import Agent
import pandas as pd 


@unique
class MessageType(Enum):
    MESSAGE = 0 
    WAKEUP = 1

    # Order related messages 
    LIMIT_ORDER = 10
    MARKET_ORDER = 11
    CANCEL_ORDER = 12
    MODIFY_ORDER = 13
    ORDER_ACCEPTED = 14
    ORDER_CANCELLED = 15
    ORDER_EXECUTED = 16
    ORDER_SUBMITTED = 17
    ORDER_MODIFIED = 18

   # Market related messages
    MARKET_OPEN = 20
    MARKET_CLOSE = 21
    MARKET_DATA = 22

    # Information related messages
    WHEN_MARKET_OPEN = 30
    WHEN_MARKET_CLOSE = 31
    QUERY_LAST_TRADE = 32
    QUERY_SPERAD = 33
    QUERY_ORDER_STREAM = 34
    QUERY_TRANSACTED_VOLUME = 35
    MARKET_DATA_SUBSCRIPTION_REQUEST = 36
    MARKET_DATA_SUBSCRIPTION_CANCELLATION = 37

    def __lt__(self, other):
        return self.value < other.value 


class Message:

  uniq = 0
  message_list = []

  @classmethod
  def get_message_by_id(cls, message_id):
     return cls.message_list[message_id] if message_id < len(cls.message_list) else None

  def __init__ (self, mtype:MessageType, 
                sender: Agent|int,
                recipient: Agent|int,
                send_time: pd.Timestamp,
                content: dict = {}
                ):
    
    self.message_type = MessageType.MESSAGE
    self.id = Message.uniq
    Message.uniq += 1
    Message.message_list.append(self)
    if sender is not None:
        if isinstance(sender, Agent):
            self.sender = sender
        else:
            self.sender = Agent.get_agent_by_id(sender)
    else:
        raise ValueError("Sender cannot be None")
    
    if recipient is not None:
        if isinstance(recipient, Agent):
            self.recipient = recipient
        else:
            self.recipient = Agent.get_agent_by_id(recipient)
    else:
        raise ValueError("Recipient cannot be None")

    if send_time is not None:
        if isinstance(send_time, pd.Timestamp):
            self.send_time = send_time
        else:
            raise ValueError("send_time must be a pd.Timestamp")
    else:
        raise ValueError("send_time cannot be None")
    
    self.content = content 


  def __lt__(self, other):
    # Required by Python3 for this object to be placed in a priority queue.
    # If we ever decide to place something on the queue other than Messages,
    # we will need to alter the below to not assume the other object is
    # also a Message.

    return (self.uniq < other.id)


  def __str__(self):
    # Make a printable representation of this message.
    return f"{self.message_type} from {self.sender} to {self.recipient} at {self.send_time}: {self.content}"
  

