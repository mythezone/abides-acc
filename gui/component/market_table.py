from rich.table import Table
from rich.console import Console
from rich import box
from rich.panel import Panel
from collections import OrderedDict


class MarketKTable:
    def __init__(self, title="Daily K Market Table", date="", mode="simple"):
        self.console = Console()
        self.title = title
        self.date = date
        self.mode = mode
        self.table = Table(box=box.SIMPLE_HEAVY)
        self.table.add_column("Code", justify="center")
        self.table.add_column("Open", justify="right")
        self.table.add_column("High", justify="right")
        self.table.add_column("Low", justify="right")
        self.table.add_column("Close", justify="right")
        self.table.add_column("Volume", justify="right")
        if self.mode == "detailed":
            self.table.add_column("Turnover", justify="right")
            self.table.add_column("Amplitude", justify="right")
            self.table.add_column("Change%", justify="right")
            self.table.add_column("Change", justify="right")
            self.table.add_column("Turnover Rate", justify="right")
        self.data = OrderedDict()

    def set_date(self, date_str):
        self.date = date_str

    def add_stock_data(self, code, info):
        self.data[code] = info
        self._sort_data()

    def update_stock_data(self, code, **kwargs):
        if code in self.data:
            self.data[code].update(kwargs)
            self._sort_data()

    def _sort_data(self):
        def safe_amount(item):
            try:
                return (
                    float(item[1].get("turnover", 0))
                    if item[1].get("turnover", 0) is not None
                    else 0
                )
            except (ValueError, TypeError):
                return 0

        self.data = OrderedDict(
            sorted(self.data.items(), key=safe_amount, reverse=True)
        )

    def clear_data(self):
        self.data = OrderedDict()
        self.date = ""

    def render(self):
        table = Table(box=box.SIMPLE_HEAVY)
        table.add_column("code", justify="center")
        table.add_column("open", justify="right")
        table.add_column("high", justify="right")
        table.add_column("low", justify="right")
        table.add_column("close", justify="right")
        table.add_column("volume", justify="right")
        if self.mode == "detailed":
            table.add_column("turnover", justify="right")
            table.add_column("amplitude", justify="right")
            table.add_column("change_percent", justify="right")
            table.add_column("change_amount", justify="right")
            table.add_column("turnover_rate", justify="right")

        for code, info in list(self.data.items())[:5]:
            row = [
                code,
                f"{float(info.get('open', 0)):.2f}",
                f"{float(info.get('high', 0)):.2f}",
                f"{float(info.get('low', 0)):.2f}",
                f"{float(info.get('close', 0)):.2f}",
                f"{int(info.get('volume', 0)):,}"[:7],
            ]
            if self.mode == "detailed":
                row.extend(
                    [
                        f"{info.get('turnover', 'N/A')}",
                        f"{info.get('amplitude', 'N/A')}",
                        f"{info.get('change_percent', 'N/A')}",
                        f"{info.get('change_amount', 'N/A')}",
                        f"{info.get('turnover_rate', 'N/A')}",
                    ]
                )
            table.add_row(*row)
        return Panel(table, title=f"{self.title} - {self.date}")
