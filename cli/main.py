from typing import Optional
import datetime
import typer
from rich.console import Console
from rich.panel import Panel
from rich.spinner import Spinner
from rich.live import Live
from rich.columns import Columns
from rich.markdown import Markdown
from rich.layout import Layout
from rich.text import Text
from rich.live import Live
from rich.table import Table
from collections import deque
import time
from rich.tree import Tree
from rich import box
from rich.align import Align
from rich.rule import Rule


console = Console()
app = typer.Typer(
    name="CALIBRAX",
    help="CALIBRAX CLI: Financial Market Simulation and Benchmarking Tool",
    add_completion=True,
)


@app.command(name="version")
def version():
    console.print("CALIBRAX CLI Version 1.0.0", style="bold green")


@app.command()
def goodbye(name: str, formal: bool = False):
    """
    Say goodbye to the user.
    """
    if formal:
        console.print(
            f"Goodbye, {name}. It was a pleasure to assist you.", style="bold red"
        )
    else:
        console.print(f"See you later, {name}!", style="bold red")


if __name__ == "__main__":
    # Run the CLI application
    app()
