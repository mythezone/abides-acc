from textual.widgets import Static
from textual.containers import Vertical
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from database.redis_client import RedisClient
import ast


class Agent:
    def __init__(self, agent_id, status, portfolio):
        self.id = agent_id
        self.status = status
        self.portfolio = portfolio
        self.pnl = portfolio.get("pnl", 0.0)

    @classmethod
    def from_dict(cls, agent_id, data: dict):
        return cls(agent_id, data["status"], data["portfolio"])

    def update(self, data: dict):
        self.status = data["status"]
        self.portfolio = data["portfolio"]
        self.pnl = self.portfolio.get("pnl", 0.0)

    def color_hex(self):
        # Clamp pnl to [-255, 255]
        v = max(-255.0, min(255.0, self.pnl))
        if v > 0:
            r = int(128 + 0.5 * v)
            g = int(128 - 0.5 * v)
        else:
            r = int(128 - 0.5 * (-v))
            g = int(128 + 0.5 * (-v))
        b = 128
        # Clamp RGB between 0~255
        r = max(0, min(255, r))
        g = max(0, min(255, g))
        return f"#{r:02x}{g:02x}{b:02x}"

    def tooltip_render(self):
        # 构建格式化多行文本，带 rich markup
        lines = []
        lines.append("[b magenta]Holdings:[/b magenta]")
        holdings = self.portfolio.get("holdings", {})
        for sym, qty in holdings.items():
            lines.append(f"[cyan]{sym}[/cyan]: {qty}")
        lines.append(
            f"[b yellow]Cash:[/b yellow] {self.portfolio.get('cash', 0.0):.2f}"
        )
        pnl_value = self.pnl
        pnl_color = "red" if pnl_value >= 0 else "green"
        lines.append(f"[b {pnl_color}]PnL:[/b {pnl_color}] {pnl_value:+.2f}%")
        return "\n".join(lines)


class AgentPanel(Static):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.r = RedisClient().get_client()
        self.agents: dict[str, Agent] = {}
        self.agent_widgets: dict[str, Static] = {}

    async def on_mount(self) -> None:
        self.set_interval(1.0, self.refresh_data)

    def refresh_data(self):
        try:
            agents_raw = self.r.hgetall("agent_status")
            current_ids = set()
            for k, v in agents_raw.items():
                aid = k.decode()
                current_ids.add(aid)
                info = ast.literal_eval(v.decode())
                if aid in self.agents:
                    # update existing agent
                    self.agents[aid].update(info)
                    agent = self.agents[aid]
                    widget = self.agent_widgets[aid]
                else:
                    # create new agent and widget
                    agent = Agent.from_dict(aid, info)
                    self.agents[aid] = agent
                    widget = Static(classes="agent-card")
                    self.agent_widgets[aid] = widget
                    self.mount(widget)

                # Determine status color
                if agent.status.lower() == "wakeup":
                    status_color = "green"
                elif agent.status.lower() == "sleep":
                    status_color = "grey50"
                else:
                    status_color = "yellow"

                # Determine pnl color
                pnl_color = "red" if agent.pnl >= 0 else "green"

                text = Text.from_markup(
                    f"[b {status_color}]{agent.status}[/b {status_color}]\n"
                    f"[b {pnl_color}]pnl: {agent.pnl:+.2f}%[/b {pnl_color}]",
                    justify="center",
                )

                panel = Panel(
                    text,
                    title=agent.id,
                    style=f"on {agent.color_hex()}",
                    border_style="white",
                )
                widget.update(panel)
                widget.tooltip = agent.tooltip_render()

            # Remove widgets and agents that no longer exist
            removed_ids = set(self.agents.keys()) - current_ids
            for rid in removed_ids:
                widget = self.agent_widgets.pop(rid)
                self.agents.pop(rid)
                widget.remove()

        except Exception:
            self.update(Text("Unable to read Agent data", style="italic"))
            return
