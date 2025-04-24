from agent import *
import numpy as np
from rich import print
from .simulator import Simulator
from util import util


class Agents:
    def __init__(self, simulator, debug=True):
        self.simulator: Simulator = simulator
        self.debug = debug
        self.agents = []
        self.agent_types = set()
        self.agent_count = 0

    def add_agent(self, agent_type, symbols, num_agents=1):
        if agent_type == "ExchangeAgent":
            symbols = symbols.split(",")
            self.agents.extend(
                [
                    ExchangeAgent(
                        id=0,
                        name="EXCHANGE_AGENT",
                        type="ExchangeAgent",
                        mkt_open=self.simulator.mkt_open,
                        mkt_close=self.simulator.mkt_close,
                        symbols=symbols,
                        log_orders=self.simulator.exchange_log_orders,
                        pipeline_delay=0,
                        computation_delay=0,
                        stream_history=self.simulator.stream_history_length,
                        book_freq=self.simulator.book_freq,
                        wide_book=True,
                        random_state=np.random.RandomState(
                            seed=np.random.randint(low=0, high=2**32, dtype="uint64")
                        ),
                    )
                ]
            )
            self.agent_count += 1
            self.agent_types.add(agent_type)

        elif agent_type == "NoiseAgent":
            for i in range(num_agents):
                self.agents.append(
                    NoiseAgent(
                        id=self.agent_count + i,
                        name=f"NoiseAgent {i}",
                        type="NoiseAgent",
                        symbol_name=symbols,
                        cash=self.simulator.starting_cash,
                        wakeup_time=util.get_wake_time(
                            self.simulator.mkt_open, self.simulator.mkt_close
                        ),
                        log_orders=self.simulator.exchange_log_orders,
                        random_state=np.random.RandomState(
                            seed=np.random.randint(low=0, high=2**32, dtype="uint64")
                        ),
                    )
                )

            if self.debug:
                self.show_debug("添加交易所代理成功")

    def show_debug(self, message):
        print(f"DEBUG: {message}")
        for agent in self.agents:
            print(f"代理名称: {agent.name}")
            print(f"代理类型: {agent.type}")
