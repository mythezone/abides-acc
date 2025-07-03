from textual.widgets import Static
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from datetime import datetime
from textual.timer import Timer
from rich.console import Group
from rich.style import Style
from textual.widgets import Static
from textual.reactive import reactive
from rich.panel import Panel
from rich.text import Text
from database.redis_client import RedisClient


class InfoPanel(Static):
    def render(self) -> Panel:
        logo_lines = [
            " ╔═╗  ╔══╗ ╔══╗╔═══╗",
            " ║╔╝  ║╔╗║ ╚╣╠╝╚╗╔╗║",
            "╔╝╚╗╔╗║╚╝╚╗ ║║  ║║║║",
            "╚╗╔╝╠╣║╔═╗║ ║║  ║║║║",
            " ║║ ║║║╚═╝║╔╣╠╗╔╝╚╝║",
            " ╚╝ ╚╝╚═══╝╚══╝╚═══╝",
        ]
        # Create Text for logo with cyan-blue gradient style (fiBID)
        logo_text = Text()
        gradient_colors = [
            "#00ffff",
            "#00bfff",
            "#007fff",
            "#005f7f",
            "#003f5f",
            "#001f2f",
        ]
        for i, line in enumerate(logo_lines):
            color = gradient_colors[i % len(gradient_colors)]
            logo_text.append(line + "\n", style=Style(color=color, bold=True))
        # Create welcome and version text
        welcome = Text("欢迎使用 CALIBRAEX 仿真系统", style="bold yellow")
        version = Text("Version: 0.2", style="bold green")
        # Group them vertically
        group = Group(
            Align.center(logo_text),
            Align.center(welcome),
            Align.center(version),
        )
        return Panel(group, title="系统信息", border_style="bright_cyan")


class OperationPanel(Static):
    operation_text = reactive("无操作数据 (No operation data)")
    current_time_str = reactive("--")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.r = RedisClient().get_client()

    def on_mount(self) -> None:
        self.set_interval(1.0, self.refresh_data)

    def refresh_data(self, *args, **kwargs):
        try:
            op = self.r.get("current_operation")
            if op:
                self.operation_text = op.decode()
            else:
                self.operation_text = "无操作数据 (No operation data)"
        except Exception:
            self.operation_text = "Redis读取失败"

        self.operation_text += "\n"

        try:
            time_bytes = self.r.get("current_time")
            if time_bytes:
                time_str = time_bytes.decode()
                try:
                    timestamp = float(time_str)
                    if timestamp > 1e11:
                        timestamp = timestamp / 1000
                    dt = datetime.fromtimestamp(timestamp)
                    self.current_time_str = dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                except Exception:
                    self.current_time_str = time_str or "--"
            else:
                self.current_time_str = "--"
        except Exception:
            self.current_time_str = "--"

    def render(self) -> Panel:
        op_text = Text(self.operation_text, style="blue")
        time_text = Text(self.current_time_str, style="bold cyan")
        group = Group(
            Align.center(op_text),
            Align.center(time_text),
        )
        return Panel(group, title="当前操作", border_style="blue")
