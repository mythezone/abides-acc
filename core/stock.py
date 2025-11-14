import enum
import os
from tkinter import E
from token import STAR
import numpy as np
import pandas as pd
from typing import List
import random
import akshare as ak
import datetime
from datetime import datetime as dt


CACHE_FOLDER = "history/stock_cache"
START_DATE = "20050101"
END_DATE = dt.today().strftime("%Y%m%d")


class Stock:

    def __init__(self, code: str):
        self.code = code
        default_file = os.path.join(CACHE_FOLDER, f"{self.code}.csv")
        os.makedirs(CACHE_FOLDER, exist_ok=True)
        if not os.path.exists(default_file):
            # Fetch data from akshare
            # print(f"Fetching data for {self.code} from akshare.")
            self.real_history = ak.stock_zh_a_hist(
                stock=self.code,
                period="daily",
                # start_date=START_DATE,
                end_date=END_DATE,
                adjust="hfq",
            )

            self.real_history.to_csv(default_file, index=False)
        else:
            # Load data from cache
            # print(f"Loading data for {self.code} from cache.")
            self.real_history = pd.read_csv(default_file)

    def get_real_ohlc(self, date: str):
        date = pd.to_datetime(date).strftime("%Y-%m-%d")
        if date not in self.real_history["日期"].values:
            return {
                "日期": date,
                "股票代码": self.code,
                "开盘": None,
                "收盘": None,
                "最高": None,
                "最低": None,
                "成交量": None,
                "成交额": None,
                "振幅": None,
                "涨跌幅": None,
                "涨跌额": None,
                "换手率": None,
            }
        else:
            return (
                self.real_history[self.real_history["日期"] == date].iloc[0].to_dict()
            )

class EFT:
    def __init__(self, portfolio: List[Stock]):
        self.portfolio = portfolio

if __name__ == "__main__":
    stock = Stock("000001")
    print(stock.get_real_ohlc("2005-05-09"))  # Should return None values for this date
