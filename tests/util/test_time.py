from datetime import date, datetime
from util.time import make_progress_calculator


def test_progress_calculator_sse():
    trading_days = [date(2025, 6, 24), date(2025, 6, 25), date(2025, 6, 26)]
    progress_fn = make_progress_calculator(trading_days, exchange="SSE")

    # 上午10:30，第一天上午盘中间，大约占整个仿真1/6
    test_time = datetime(2025, 6, 24, 10, 30)
    percent = progress_fn(test_time)
    assert 5 < percent < 25

    # 第二天下午15:00，应该刚好过两天，约2/3
    test_time2 = datetime(2025, 6, 25, 15, 0)
    percent2 = progress_fn(test_time2)
    assert 65 < percent2 < 70

    # 模拟结束后时间，进度应为100%
    test_time3 = datetime(2025, 6, 27, 10, 0)
    percent3 = progress_fn(test_time3)
    assert percent3 == 100.0
