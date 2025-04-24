import pandas as pd
import numpy as np

from typing import List, Dict

from core.base import Trackable, RandomState
from core.message import Message, MessageType
from core.clock import Clock
from core.logger import Logger

# 在类型检测时不会出现循环引用错误
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from core.kernel import Kernel


class Agent(Trackable):
    _agent_id = 0
    _all_agents = []

    def __init__(self, *args, kernel: "Kernel" = None, **kwargs):
        self.agent_id = Agent._agent_id
        Agent._agent_id += 1
        Agent._all_agents.append(self)

        super().__init__()

        # What time does the agent think it is?  Should be updated each time
        # the agent wakes via wakeup or receiveMessage.  (For convenience
        # of reference throughout the Agent class hierarchy, NOT THE
        # CANONICAL TIME.)
        self.kernel = kernel
        self.inbox = []
        self.random_state = RandomState().state
        # self.logEvent("AGENT_TYPE", type)

        self.args = args
        for key, value in kwargs.items():
            setattr(self, key, value)

        self.clock = Clock()

        self.initiate()

    def initiate(self):
        msg = Message(
            message_type=MessageType.MESSAGE,
            sender_id=self.agent_id,
            send_time=self.kernel.now(),
            recive_time=self.kernel.now(),
            content=f"{self.name} Initiated",
        )
        self.send(msg, recive_delay=0)
        self.set_next_wakeup()

    def set_next_wakeup(self):
        time_delta = self.wakeup_delay()
        wakeup_time = self.clock.future(nanoseconds=time_delta)
        msg = Message(
            message_type=MessageType.WAKEUP,
            sender_id=self.agent_id,
            send_time=self.clock.now(),
            recive_time=wakeup_time,
            content=f"{self.name} waked up",
        )
        self.send(msg)

    def send(self, message: Message, recive_delay=0):
        self.kernel.inbox.put(message, recive_delay=recive_delay)

    @property
    def name(self):
        return self.__class__.__name__ + "-" + str(self.agent_id)

    def wakeup_delay(self):
        return self.random_state.randint(1000, 10000)

    def wakeup(self):
        # handle message in self.inbox
        self.set_next_wakeup()

    @classmethod
    def get_instance_by_id(cls, id_: int):
        if id_ < len(cls._all_agents):
            return cls._all_agents[id_]
        else:
            raise ValueError(
                f"Instance with ID {id_} does not exist in {cls.__name__}."
            )

    @staticmethod
    def size():
        return len(Agent._all_agents)

    @classmethod
    def __class_getitem__(cls, id_: int):
        return cls.get_instance_by_id(id_)

    # Delays
    def computation_delay(self, low=100, high=300):
        return self.random_state.randint(low, high)

    def order_delay(self, low=100, high=200):
        return self.random_state.randint(low, high)

    def distance_delay(self, low=1, high=100):
        return self.random_state.randint(low, high)
