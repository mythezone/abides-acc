from turtle import title
from rich import align
from textual.widgets import Static, TabbedContent, TabPane
from textual.app import ComposeResult
from textual.containers import Horizontal
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
import json
from database.redis_client import RedisClient
from datetime import datetime


class LOBTable(Static):
    def __init__(self, symbol: str, bids: list, asks: list, **kwargs):
        super().__init__(**kwargs)
        self.symbol = symbol
        self.bids = bids
        self.asks = asks
        self._update_table()
        self.classes = "lob-table"

    def _update_table(self):
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Buy Price", justify="right", style="green")
        table.add_column("Buy Volume", justify="right", style="green")
        table.add_column("Sell Price", justify="right", style="red")
        table.add_column("Sell Volume", justify="right", style="red")
        for i in range(max(len(self.bids), len(self.asks))):
            bid_p, bid_v = self.bids[i] if i < len(self.bids) else ("", "")
            ask_p, ask_v = self.asks[i] if i < len(self.asks) else ("", "")
            table.add_row(str(bid_p), str(bid_v), str(ask_p), str(ask_v))
        self.update(
            Panel(table, title=f"LOB Snapshot: {self.symbol}", border_style="green")
        )

    def update_data(self, bids, asks):
        self.bids = bids
        self.asks = asks
        self._update_table()


class Transactions:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Transactions, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.r = RedisClient().get_client()
        self.cache = {}  # symbol -> list of log lines
        self._initialized = True

    def update_for_symbol(self, symbol: str, trim: int = 12):
        raw = self.r.lrange(f"trade_list:{symbol}", 0, 9)
        if not raw:
            self.cache[symbol] = []
            return
        if symbol not in self.cache:
            self.cache[symbol] = []

        existing_times = set()
        # Extract existing times from cached logs by parsing the time string in the log line
        for log_line in self.cache[symbol]:
            try:
                # log line format: [b cyan]HH:MM:SS.ffffff[/b cyan] ...
                # extract time string between [b cyan] and [/b cyan]
                start = log_line.find("[b cyan]") + len("[b cyan]")
                end = log_line.find("[/b cyan]", start)
                time_str = log_line[start:end]
                # convert time_str to datetime for comparison
                dt = datetime.strptime(time_str, "%H:%M:%S.%f")
                existing_times.add(dt)
            except Exception:
                continue

        new_logs = []
        for item in raw:
            try:
                trade = json.loads(item)
                time_val = trade.get("time", None)
                if time_val is not None:
                    dt = datetime.fromtimestamp(time_val / 1000)
                    if dt in existing_times:
                        continue
                    time_str = dt.strftime("%H:%M:%S.%f")
                else:
                    time_str = "unknown"
                agent1 = trade.get("agent1", "")
                agent2 = trade.get("agent2", "")
                price = trade.get("price", "")
                volume = trade.get("volume", "")
                log_line = (
                    f"[b cyan]{time_str}[/b cyan] "
                    f"[magenta]{agent1}[/magenta] → [magenta]{agent2}[/magenta] "
                    f"[yellow bold]@{price}[/yellow bold] ×[b]{volume}[/b]"
                )
                new_logs.append((dt if time_val is not None else None, log_line))
            except Exception:
                continue

        # Sort new logs by datetime ascending (oldest first)
        new_logs = [
            log
            for dt, log in sorted(
                new_logs, key=lambda x: x[0] if x[0] is not None else datetime.min
            )
        ]

        # Append new logs to cache
        self.cache[symbol].extend(new_logs)

        # Keep only the last trim entries
        if len(self.cache[symbol]) > trim:
            self.cache[symbol] = self.cache[symbol][-trim:]

    def get_logs(self, symbol: str):
        return self.cache.get(symbol, [])


class TransactionLogPanel(Static):
    def __init__(self, symbol: str = "", **kwargs):
        super().__init__(**kwargs)
        self.symbol = symbol

    def update_logs(self, symbol):
        self.symbol = symbol
        transactions = Transactions()
        logs = transactions.get_logs(symbol)
        text = Text()
        if not logs:
            text.append("-- No Transaction Records --", style="dim")
        else:
            for line in logs:
                text.append(Text.from_markup(line))
                text.append("\n")
        self.update(
            Panel(
                text, title=f"Transaction Records: {self.symbol}", border_style="blue"
            )
        )


class LOBPanel(Static):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.r = RedisClient().get_client()
        self.symbols = []
        self.lob_widgets = {}
        self.trans_widgets = {}

    def compose(self) -> ComposeResult:
        # 动态读取 keys 构造标签
        keys = self.r.keys("lob_snapshot:*") or []
        self.symbols = [key.decode().split(":")[1] for key in keys]
        if not self.symbols:
            self.symbols = ["(No Data)"]

        with TabbedContent(*self.symbols):
            for symbol in self.symbols:
                with TabPane(symbol, id=f"sym_{symbol}", classes="lob-panel-tab"):
                    with Horizontal():
                        lob_widget = LOBTable(symbol, [], [])
                        trans_widget = TransactionLogPanel(
                            symbol, classes="transaction-log-panel"
                        )
                        self.lob_widgets[symbol] = lob_widget
                        self.trans_widgets[symbol] = trans_widget
                        yield trans_widget
                        yield lob_widget

                        # yield Static("这是测试内容", classes="test-component")

    def on_mount(self):
        self.set_interval(1.0, self.refresh_active_tab)

    def refresh_active_tab(self):
        tabbed: TabbedContent = self.query_one(TabbedContent)
        active_id = tabbed.active or f"sym_{self.symbols[0]}"
        symbol = active_id.removeprefix("sym_")

        if symbol == "(No Data)":
            return

        try:
            raw = self.r.get(f"lob_snapshot:{symbol}")
            lob = json.loads(raw) if raw else {}
            bids = lob.get("bid", [])
            asks = lob.get("ask", [])
        except Exception:
            bids, asks = [], []

        # 更新交易记录缓存
        Transactions().update_for_symbol(symbol)

        lob_widget = self.lob_widgets.get(symbol)
        trans_widget = self.trans_widgets.get(symbol)

        if lob_widget:
            lob_widget.update_data(bids, asks)
        if trans_widget:
            trans_widget.update_logs(symbol)
