import pandas as pd
import numpy as np
import pickle
import os
from datetime import datetime, time


TRADING_DAYS_FILE = "database/info/trading_days.pkl"

with open(TRADING_DAYS_FILE, "rb") as f:
    TRADING_DAYS = pickle.load(f)


def get_trading_days(start_date: str, end_date: str):
    return [d for d in TRADING_DAYS if start_date <= d <= end_date]


def make_progress_calculator(trading_days, exchange="SZSE"):
    """
    生成一个仿真进度百分比函数，根据交易所自动设定交易时段。
    支持交易所: SSE, SZSE, HKEX, NYSE
    """
    trading_days = [
        datetime.strptime(day, "%Y-%m-%d").date() if isinstance(day, str) else day
        for day in trading_days
    ]
    exchange_sessions = {
        "SSE": [(time(9, 30), time(11, 30)), (time(13, 0), time(15, 0))],
        "SZSE": [(time(9, 30), time(11, 30)), (time(13, 0), time(15, 0))],
        "HKEX": [(time(9, 30), time(12, 0)), (time(13, 0), time(16, 0))],
        "NYSE": [(time(9, 30), time(16, 0))],
    }

    if exchange not in exchange_sessions:
        raise ValueError(f"Unsupported exchange: {exchange}")

    trading_sessions = exchange_sessions[exchange]

    intervals = []
    for day in trading_days:
        for start_t, end_t in trading_sessions:
            intervals.append(
                (datetime.combine(day, start_t), datetime.combine(day, end_t))
            )

    total_seconds = sum((end - start).total_seconds() for start, end in intervals)

    def progress(current_datetime):
        elapsed = 0
        for start, end in intervals:
            if current_datetime >= end:
                elapsed += (end - start).total_seconds()
            elif start <= current_datetime < end:
                elapsed += (current_datetime - start).total_seconds()
                break
            elif current_datetime < start:
                break
        return round(
            min(100.0, (elapsed / total_seconds) * 100) if total_seconds else 0.0, 2
        )

    return progress


def test_time_process(start_time_stamp: pd.Timestamp, low_bound: int, up_bound: int):
    random_time_delta = pd.Timedelta(
        f"{low_bound + (up_bound - low_bound) * np.random.rand() * 10} seconds"
    )
    test_time = start_time_stamp + random_time_delta
    return test_time
