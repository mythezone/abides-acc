import pytest
import pandas as pd
from core.portfolio import Portfolio
from unittest.mock import MagicMock
from core.symbol import Symbol


def test_initialize_random_portfolio():
    symbols = [Symbol("000001"), Symbol("000002"), Symbol("000003")]

    portfolio = Portfolio()
    portfolio.initialize_random_portfolio(
        symbols,
        prev_date="2024-06-25",
        min_shares=10,
        max_shares=20,
        min_cash=1000,
        max_cash=2000,
    )

    assert portfolio.cash >= 1000
    assert portfolio.cash <= 2000
    assert len(portfolio.holdings) == 3
    for sym in portfolio.holdings:
        assert 10 <= portfolio.holdings[sym] <= 20
    assert portfolio.initial_value > 0


def test_current_total_value():
    portfolio = Portfolio()
    portfolio.cash = 5000
    portfolio.holdings = {"SYM1": 100, "SYM2": 200}

    current_prices = {"SYM1": 20.0, "SYM2": 30.0}
    total_value = portfolio.current_total_value(current_prices)
    expected_value = 5000 + 100 * 20.0 + 200 * 30.0
    assert total_value == expected_value


def test_record_and_average_return():
    portfolio = Portfolio()
    portfolio.cash = 1000
    portfolio.holdings = {"SYM1": 50}
    current_prices_day1 = {"SYM1": 20.0}
    current_prices_day2 = {"SYM1": 22.0}
    current_prices_day3 = {"SYM1": 21.0}

    portfolio.record_daily_value("2024-06-25", current_prices_day1)
    portfolio.record_daily_value("2024-06-26", current_prices_day2)
    portfolio.record_daily_value("2024-06-27", current_prices_day3)

    assert len(portfolio.daily_values) == 3
    avg_return = portfolio.average_daily_return()
    assert isinstance(avg_return, float)


def test_snapshot_and_daily_logs():
    portfolio = Portfolio()
    portfolio.cash = 1000
    portfolio.holdings = {"SYM1": 50, "SYM2": 30}
    current_prices = {"SYM1": 20.0, "SYM2": 25.0}

    date = "2024-06-28"
    portfolio.record_daily_value(date, current_prices)

    assert len(portfolio.daily_logs) == 1
    log = portfolio.daily_logs[0]
    assert f"Date: {date}" in log
    assert "SYM1" in log and "SYM2" in log
    assert "Total Value" in log
