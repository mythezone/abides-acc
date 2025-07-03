from textual.widgets import Static
from rich.panel import Panel
from rich.table import Table
from database.redis_client import RedisClient


class MarketPanel(Static):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.r = RedisClient().get_client()

    def on_mount(self) -> None:
        self.set_interval(1.0, self.refresh_data)

    def refresh_data(self, *args, **kwargs):
        from datetime import datetime

        try:
            date = datetime.now().strftime("%Y-%m-%d")
            data = self.r.hgetall("market_table")
            parsed = []
            for k, v in data.items():
                parsed.append((k.decode(), eval(v.decode())))
            top_symbols = sorted(
                parsed, key=lambda item: item[1].get("成交额", 0), reverse=True
            )[:5]
            table = Table(title=f"{date} Market Top 5", show_lines=True)
            table.add_column("代码")
            table.add_column("开盘", justify="right")
            table.add_column("最高", justify="right")
            table.add_column("最低", justify="right")
            table.add_column("收盘", justify="right")
            table.add_column("成交量", justify="right")
            for symbol, row in top_symbols:
                table.add_row(
                    symbol,
                    f"{row['开盘']:.2f}",
                    f"{row['最高']:.2f}",
                    f"{row['最低']:.2f}",
                    f"{row['收盘']:.2f}",
                    f"{int(row['成交量'])}",
                )
        except Exception:
            table = Table(title="Market Top 5 (No Data)", show_lines=True)
            table.add_column("代码")
            table.add_column("开盘", justify="right")
            table.add_column("最高", justify="right")
            table.add_column("最低", justify="right")
            table.add_column("收盘", justify="right")
            table.add_column("成交量", justify="right")
        self.update(Panel(table, title="市场行情", border_style="yellow"))
