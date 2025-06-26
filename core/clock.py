import pandas as pd
from core.base import Singleton
import numpy as np


class Clock(metaclass=Singleton):
    def __init__(self, initial_time: str = "now"):
        self.initial_time = initial_time
        if initial_time == "now":
            self.current_time = pd.Timestamp.now()
            self.init_time = self.current_time.isoformat()
        else:
            try:
                self.current_time = pd.Timestamp(initial_time)
            except Exception:
                # 若解析失败，设为当前时间
                self.current_time = pd.Timestamp.now()
                self.init_time = self.current_time.isoformat()

    def now(self):
        """获取当前时间"""
        return self.current_time

    def tick(
        self,
        hours: int = 0,
        minutes: int = 0,
        seconds: int = 0,
        milliseconds: int = 0,
        microseconds: int = 0,
        nanoseconds: int = 0,
    ):
        """时间前进指定时间"""
        self.current_time += pd.Timedelta(
            hours=hours,
            minutes=minutes,
            seconds=seconds,
            milliseconds=milliseconds,
            microseconds=microseconds,
            nanoseconds=nanoseconds,
        )

    def future(
        self,
        hours: int = 0,
        minutes: int = 0,
        seconds: int = 0,
        milliseconds: int = 0,
        microseconds: int = 0,
        nanoseconds: int = 0,
    ):
        """获取前进指定时间的时间戳"""
        return self.current_time + pd.Timedelta(
            hours=hours,
            minutes=minutes,
            seconds=seconds,
            milliseconds=milliseconds,
            microseconds=microseconds,
            nanoseconds=nanoseconds,
        )

    def tick_to(self, target_time: str):
        """时间跳转到指定时间"""
        try:
            self.current_time = pd.Timestamp(target_time)
        except Exception:
            # 若解析失败，设为当前时间
            raise ValueError(f"Invalid target time format: {target_time}")

    def reset(self):
        """重置当前时间为初始时间"""
        if self.initial_time == "":
            self.current_time = pd.Timestamp.now()
        else:
            try:
                self.current_time = pd.Timestamp(self.initial_time)
            except Exception:
                # 若解析失败，设为当前时间
                self.current_time = pd.Timestamp.now()

    def __str__(self):
        """返回时间戳的ISO 8601格式"""
        return self.current_time.isoformat()

    @staticmethod
    def real_time():
        """获取当前墙钟时间"""
        return pd.Timestamp.now()


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
