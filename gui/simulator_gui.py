from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import Reactive
from textual.widgets import Header, Footer, Rule
from textual import events
from textual.binding import Binding

from gui.widgets.info_panel import InfoPanel, OperationPanel
from gui.widgets.agent_panel import AgentPanel
from gui.widgets.market_panel import MarketPanel
from gui.widgets.lob_panel import LOBPanel
from gui.widgets.footer import MyFooter
from gui.widgets.help_modal import HelpScreen

# from gui.widgets.test_webview_panel import TestWebViewPanel


class SimulatorApp(App):
    CSS_PATH = "style/default.tcss"
    BINDINGS = [
        Binding(key="q", action="quit", description="Quit the app"),
        Binding(
            key="h",
            action="show_help",
            description="Show help screen",
            key_display="?",
        ),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True, icon="🧾 menu", id="header")
        yield Vertical(
            Horizontal(
                Vertical(
                    InfoPanel(id="info"),
                    OperationPanel(id="operation"),
                    # SimTimePanel(id="sim_time"),
                    id="info_panels",
                ),
                MarketPanel(id="market"),
                LOBPanel(id="lob_panel"),
                # 添加测试用 tab panel
                id="main_view",
            ),
            # Rule(line_style="dashed", classes="rule"),
            AgentPanel(id="agents-list"),
            # TestWebViewPanel(id="test_web"),
            id="body",
        )
        yield Footer()

    def action_show_help(self):
        self.push_screen(HelpScreen())

    async def on_mount(self) -> None:
        self.query_one("#operation", OperationPanel).operation_text = (
            "Loading Stock data..."
        )


if __name__ == "__main__":
    app = SimulatorApp()
    app.run()
