from rich.table import Table
from rich.console import Console
from rich import box
from rich.panel import Panel
from collections import OrderedDict


class MarketKTable:
    def __init__(self, title="日K行情表", date="", mode="simple"):
        self.console = Console()
        self.title = title
        self.date = date
        self.mode = mode
        self.table = Table(box=box.SIMPLE_HEAVY)
        self.table.add_column("代码", justify="center")
        self.table.add_column("开盘", justify="right")
        self.table.add_column("最高", justify="right")
        self.table.add_column("最低", justify="right")
        self.table.add_column("收盘", justify="right")
        self.table.add_column("成交量", justify="right")
        if self.mode == "detailed":
            self.table.add_column("成交额", justify="right")
            self.table.add_column("振幅", justify="right")
            self.table.add_column("涨跌幅", justify="right")
            self.table.add_column("涨跌额", justify="right")
            self.table.add_column("换手率", justify="right")
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
                    float(item[1].get("成交额", 0))
                    if item[1].get("成交额", 0) is not None
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
        table.add_column("代码", justify="center")
        table.add_column("开盘", justify="right")
        table.add_column("最高", justify="right")
        table.add_column("最低", justify="right")
        table.add_column("收盘", justify="right")
        table.add_column("成交量", justify="right")
        if self.mode == "detailed":
            table.add_column("成交额", justify="right")
            table.add_column("振幅", justify="right")
            table.add_column("涨跌幅", justify="right")
            table.add_column("涨跌额", justify="right")
            table.add_column("换手率", justify="right")

        for code, info in list(self.data.items())[:5]:
            row = [
                code,
                f"{float(info.get('开盘', 0)):.2f}",
                f"{float(info.get('最高', 0)):.2f}",
                f"{float(info.get('最低', 0)):.2f}",
                f"{float(info.get('收盘', 0)):.2f}",
                f"{int(info.get('成交量', 0)):,}"[:7],
            ]
            if self.mode == "detailed":
                row.extend(
                    [
                        f"{info.get('成交额', 'N/A')}",
                        f"{info.get('振幅', 'N/A')}",
                        f"{info.get('涨跌幅', 'N/A')}",
                        f"{info.get('涨跌额', 'N/A')}",
                        f"{info.get('换手率', 'N/A')}",
                    ]
                )
            table.add_row(*row)
        return Panel(table, title=f"{self.title} - {self.date}")
