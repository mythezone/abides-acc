from rich.panel import Panel
from rich.text import Text
from rich.columns import Columns
from rich.layout import Layout
import random


class AgentPanel:
    def __init__(self, title="Agent 状态面板", parent: Layout = None):
        self.title = title
        self.parent = parent
        self.agents = {}

    def update_agent(self, agent_info: dict):
        agent_id = agent_info["agent_id"]
        if agent_id not in self.agents:
            self.agents[agent_id] = {"bgcolor": self._random_color(), **agent_info}
        else:
            # bgcolor = self.agents[agent_id]["bgcolor"]
            self.agents[agent_id].update(agent_info)
            # self.agents[agent_id]["bgcolor"] = bgcolor

    # def add_agent(self, agent_id: str):
    #     if agent_id not in self.agents:
    #         self.agents[agent_id] = {"bgcolor": self._random_color(), "status": "sleep"}

    def render(self):
        boxes = []
        for agent_id, info in self.agents.items():
            status = info.get("status", "unknown")
            border_color = "green" if status == "wakeup" else "red"
            box_text = Text(str(agent_id), justify="center")
            box = Panel(
                box_text,
                style=f"on {info['bgcolor']}",
                border_style=border_color,
                width=20,
            )
            boxes.append(box)
        panel = Panel(Columns(boxes, equal=True, expand=True), title=self.title)
        if self.parent:
            self.parent.update(panel)

    # 内部方法
    def _random_color(self):
        return f"#{random.randint(0, 0xFFFFFF):06x}"
