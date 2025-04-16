import pandas as pd
from core.base import Singleton


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
