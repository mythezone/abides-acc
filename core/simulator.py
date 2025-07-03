from calendar import c
from rich.console import Console, Group
from rich.panel import Panel
from rich.live import Live
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich.screen import Screen
from rich.prompt import Prompt
from rich.layout import Layout
from rich import print
from rich.markdown import Markdown
from rich.tree import Tree
from rich.text import Text

from typing import List, Dict, Any, Optional
from time import sleep
import random
import time
import json
from core import agent
from util.seed import seed_everything
import pandas as pd
import numpy as np


from core.symbol import Symbol
from core.kernel import Kernel
from core.clock import MarketClock
from core.message import Message, MessageType, MessageQueue

from gui.component.market_table import MarketKTable
from gui.component.agent_panel import AgentPanel


from util.time import get_trading_days, make_progress_calculator, test_time_process

# from core.kernel import Kernel
# from core.logger import Logger


class Simulator:
    def __init__(self, config_path: str = "config/test.json"):
        self.console = Console()
        self.layout = Layout()

        with open(config_path, "r") as f:
            self.config = json.load(f)

        seed_everything(self.config["simulation"]["seed"])
        self.symbols: Dict = {}

        self.init_layout()

    def init_layout(self):
        self.layout.split(
            Layout(name="title", size=4),
            Layout(name="lower", size=10),
            Layout(name="agent_panel"),
        )
        info_panel = Panel(
            Group(
                Text("欢迎使用 CALIBRAEX 仿真系统", style="bold green"),
                Text(
                    f"Version: {self.config['simulation']['version']}",
                    style="bold blue",
                ),
            ),
            title="CALIBRAEX",
            border_style="red",
            height=4,
        )
        self.layout["title"].update(info_panel)
        self.layout["lower"].split_row(
            Layout(name="Operation", size=40),
            Layout(name="Info", size=30),
            Layout(name="Market", size=70),
            Layout(name="LOB"),
        )
        self.market_table = MarketKTable(
            title="市场行情",
            date=self.config["simulation"]["start_date"],
            mode=self.config["simulation"]["market_table_mode"],
        )
        self.agent_panel = AgentPanel(
            title="Agent 状态面板", parent=self.layout["agent_panel"]
        )

    def start(self):

        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed:6.2f} / {task.total}"),
        )

        with Live(self.layout, screen=True, refresh_per_second=30) as live:
            #
            # self.kernel.initialize()
            # Initialize symbols
            initiate_symbols = progress.add_task(
                "Initiate Symbols", total=len(self.config["symbols"]), start=True
            )

            for i, symbol in enumerate(self.config["symbols"]):
                progress.update(initiate_symbols, advance=1)

                s = Symbol(symbol)
                self.symbols[symbol] = s

                row_dict = s.get_real_ohlc(date=self.config["simulation"]["start_date"])
                # print(row_dict)
                self.market_table.add_stock_data(symbol, row_dict)

                sleep(0.1)
                current_op = Panel(
                    Group(
                        Text(f"当前操作：初始化股票代码 {symbol}", style="bold"),
                        progress,
                    ),
                    title="仿真进度",
                    border_style="blue",
                )
                self.layout["Operation"].update(current_op)
                table = self.market_table.render()
                self.layout["Market"].update(table)

            # Initialize agents
            current_op = Panel(
                Group(
                    Text(f"当前操作：初始化Agents", style="bold"),
                    progress,
                ),
                title="仿真进度",
                border_style="blue",
            )
            self.layout["Operation"].update(current_op)
            agent_config = self.config["kernel"]["agents"]
            all_agents_num = 0
            for ac in agent_config:
                all_agents_num += ac["num"]

            initiate_agents = progress.add_task(
                "Initiate Agents", total=all_agents_num, start=True
            )

            self.msg_queue = MessageQueue()
            self.kernel = Kernel(
                config=self.config["kernel"], message_queue=self.msg_queue
            )
            self.kernel.initialize()
            self.kernel.init_agent(
                agent_config, self.agent_panel, progress, task=initiate_agents
            )

            # Initialize simulated time

            start_time = self.config["simulation"]["start_date"]
            end_time = self.config["simulation"]["end_date"]
            exchange_type = self.config["simulation"].get("exchange", "SZSE")
            trading_days = get_trading_days(start_time, end_time)
            self.market_clock = MarketClock(trading_days, exchange=exchange_type)
            # self.simulation_progress_fn = self.market_clock.get_progress
            simulation_task = progress.add_task("Simulation", total=100, start=True)
            start_time: pd.Timestamp = pd.to_datetime(start_time)
            current_date = start_time.date()

            while True:
                start_time = self.market_clock.step_random_time(20, 60)
                if current_date != start_time.date():
                    current_date = start_time.date()
                    self.update_market_view(current_date)
                percent = self.market_clock.get_progress()
                current_op = Panel(
                    Group(
                        Text(
                            f"当前操作：{start_time.strftime('%Y-%m-%d %H:%M')} 到 {end_time}",
                            style="bold",
                        ),
                        progress,
                    ),
                    title="仿真进度",
                    border_style="blue",
                )
                progress.update(simulation_task, completed=percent)
                self.layout["Operation"].update(current_op)
                time.sleep(0.001)
                if percent >= 100.0:
                    break

    def update_market_view(self, date: pd.Timestamp):
        self.market_table.clear_data()
        self.market_table.set_date(date.strftime("%Y-%m-%d"))
        for symbol, s in self.symbols.items():
            row_dict = s.get_real_ohlc(date=date.strftime("%Y-%m-%d"))
            self.market_table.add_stock_data(symbol, row_dict)
        self.layout["Market"].update(self.market_table.render())


if __name__ == "__main__":
    simulator = Simulator()
    simulator.start()
