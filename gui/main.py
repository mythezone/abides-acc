from textual.app import App, ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Header, Footer, Button, Digits


class MarketSimulator(App):
    """A Textual app to simulate a financial market."""

    BINDINGS = [("q", "quit", "Quit")]

    def compose(self) -> ComposeResult:
        """Create the UI components."""
        yield Header()
        yield Footer()
        yield Button("Start Simulation", id="start_simulation", variant="success")
        yield Button("Stop Simulation", id="stop_simulation", variant="error")

    def action_quit(self) -> None:
        """Handle the quit action."""
        self.exit()


if __name__ == "__main__":
    app = MarketSimulator()
    app.run()
    # The app will run until the user presses 'q' or closes the window.
