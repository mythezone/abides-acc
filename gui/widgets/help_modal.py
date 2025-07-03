from textual.screen import Screen
from textual.widgets import Static, Button
from textual.containers import Vertical
from rich.text import Text


class HelpScreen(Screen):
    BINDINGS = [("escape", "app.pop_screen", "关闭")]

    def compose(self):
        yield Vertical(
            Static(
                Text(
                    "欢迎使用 CALIBRAEX/fiBID 仿真系统！\n\n"
                    "[b]快捷键：[/b]\n"
                    "F1/H - 帮助\n"
                    "Q    - 退出\n"
                    "Tab  - 切换面板\n"
                    "←/→  - 切换合约\n"
                    "R    - 刷新\n"
                    "Space- 暂停/继续\n",
                    style="bold cyan",
                )
            ),
            Button("关闭", id="close_help"),
        )

    def on_button_pressed(self, event):
        if event.button.id == "close_help":
            self.app.pop_screen()
