import pandas as pd
import numpy as np

EXCHANGE_SESSIONS = {
    "SSE": [
        (pd.Timestamp("09:30").time(), pd.Timestamp("11:30").time()),
        (pd.Timestamp("13:00").time(), pd.Timestamp("15:00").time()),
    ],
    "SZSE": [
        (pd.Timestamp("09:30").time(), pd.Timestamp("11:30").time()),
        (pd.Timestamp("13:00").time(), pd.Timestamp("15:00").time()),
    ],
    "HKEX": [
        (pd.Timestamp("09:30").time(), pd.Timestamp("12:00").time()),
        (pd.Timestamp("13:00").time(), pd.Timestamp("16:00").time()),
    ],
    "NYSE": [(pd.Timestamp("09:30").time(), pd.Timestamp("16:00").time())],
}


class KernelClock:
    def __init__(self, initial_time: str = "now", trading_days=None, exchange="SZSE"):
        self.real_start_time = pd.Timestamp.now()
        self.initial_time = initial_time
        self.exchange = exchange
        self.sessions = EXCHANGE_SESSIONS[exchange]
        self.trading_days = [
            pd.to_datetime(day).date() if isinstance(day, str) else day
            for day in (trading_days or [])
        ]
        self.day_index = 0
        if initial_time == "now":
            self.simulate_time = self.real_start_time
        else:
            try:
                self.simulate_time = pd.Timestamp(initial_time)
            except Exception:
                self.simulate_time = pd.Timestamp.now()

    def now(self):
        return self.simulate_time

    def tick(self, **kwargs):
        self.simulate_time += pd.Timedelta(**kwargs)

    def skip_break(self):
        if not self.trading_days:
            return
        current_date = self.simulate_time.date()
        time_only = self.simulate_time.time()
        for start, end in self.sessions:
            if time_only < start:
                self.simulate_time = pd.Timestamp.combine(current_date, start)
                return
            elif start <= time_only < end:
                return
        self.next_trading_day()

    def next_trading_day(self):
        self.day_index += 1
        if self.day_index < len(self.trading_days):
            next_date = self.trading_days[self.day_index]
            self.simulate_time = pd.Timestamp.combine(next_date, self.sessions[0][0])

    def is_break_time(self):
        time_only = self.simulate_time.time()
        in_session = False
        for start, end in self.sessions:
            if start <= time_only < end:
                in_session = True
                break
        return not in_session

    def is_market_closed(self):
        return self.simulate_time.date() not in self.trading_days


class MarketClock:
    def __init__(self, trading_days, exchange="SZSE"):
        if exchange not in EXCHANGE_SESSIONS:
            raise ValueError(f"Unsupported exchange: {exchange}")
        self.sessions = EXCHANGE_SESSIONS[exchange]
        self.trading_days = [
            pd.to_datetime(day).date() if isinstance(day, str) else day
            for day in trading_days
        ]
        self.intervals = []
        for day in self.trading_days:
            for start_t, end_t in self.sessions:
                self.intervals.append(
                    (
                        pd.Timestamp.combine(day, start_t),
                        pd.Timestamp.combine(day, end_t),
                    )
                )
        self.total_seconds = sum(
            (end - start).total_seconds() for start, end in self.intervals
        )
        self.current_index = 0
        self.current_time = self.intervals[0][0] if self.intervals else None

    def get_progress(self):
        elapsed = 0
        for start, end in self.intervals:
            if self.current_time >= end:
                elapsed += (end - start).total_seconds()
            elif start <= self.current_time < end:
                elapsed += (self.current_time - start).total_seconds()
                break
            elif self.current_time < start:
                break
        return round(
            (
                min(100.0, (elapsed / self.total_seconds) * 100)
                if self.total_seconds
                else 0.0
            ),
            2,
        )

    def step_random_time(self, low_bound: int, up_bound: int):
        if self.current_index >= len(self.intervals):
            return self.current_time

        step = low_bound + (up_bound - low_bound) * np.random.rand()
        while step > 0 and self.current_index < len(self.intervals):
            start, end = self.intervals[self.current_index]
            remaining = (end - self.current_time).total_seconds()

            if step < remaining:
                self.current_time += pd.Timedelta(seconds=step)
                step = 0
            else:
                # Jump to the start of the next interval
                step -= remaining
                self.current_index += 1
                if self.current_index < len(self.intervals):
                    self.current_time = self.intervals[self.current_index][0]
                else:
                    self.current_time = end
        return self.current_time
