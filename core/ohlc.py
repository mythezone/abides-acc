import pandas as pd
from typing import Optional
from core.logger import Logger


class OHLCAggregator:
    def __init__(self, stock: str, freq: str = "1s", logger: Optional[Logger] = None):
        self.stock = stock
        self.freq = pd.Timedelta(freq)
        self.logger = logger
        self.window_start: Optional[pd.Timestamp] = None
        self.open = None
        self.high = None
        self.low = None
        self.close = None
        self.volume = 0.0

    def _window_floor(self, ts: pd.Timestamp) -> pd.Timestamp:
        # floor to nearest freq since day start
        return ts.floor(self.freq)

    def _flush(self):
        if (
            self.window_start is not None
            and self.open is not None
            and self.close is not None
            and self.logger is not None
        ):
            self.logger.ohlc_log(
                stock_name=self.stock,
                kernel_time=self.window_start,
                open_=float(self.open),
                high=float(self.high),
                low=float(self.low),
                close=float(self.close),
                volume=float(self.volume),
            )

    def update(self, ts: pd.Timestamp, price: float, volume: float = 0.0):
        win = self._window_floor(ts)
        if self.window_start is None:
            self.window_start = win
            self.open = self.high = self.low = self.close = price
            self.volume = volume
            return
        if win != self.window_start:
            # emit bar
            self._flush()
            # reset for new window
            self.window_start = win
            self.open = self.high = self.low = self.close = price
            self.volume = volume
        else:
            self.close = price
            self.high = max(self.high, price)
            self.low = min(self.low, price)
            self.volume += volume

    def flush_all(self):
        self._flush()

