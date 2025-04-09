import numpy as np 
import pandas as pd 
import datetime as dt 

class Simulator:
    def __init__(self,debug=True):
        self.debug = debug
        pass 

    def init(self,historical_date, start_time, end_time,stream_history_length, log_dir, verbose, exchange_log_orders, book_freq,
             starting_cash):

        self.historical_date = historical_date
        self.start_time = dt.datetime.strptime(start_time, '%H:%M:%S').time()
        self.end_time = dt.datetime.strptime(end_time, '%H:%M:%S').time()
        self.stream_history_length = stream_history_length
        self.log_dir = log_dir
        self.verbose = verbose
        self.exchange_log_orders = exchange_log_orders
        self.book_freq = book_freq
        self.starting_cash = starting_cash


        self.mkt_open = historical_date + pd.to_timedelta(self.start_time.strftime('%H:%M:%S'))
        self.mkt_close = historical_date + pd.to_timedelta(self.end_time.strftime('%H:%M:%S'))
        self.noise_mkt_open = historical_date + pd.to_timedelta("09:00:00")
        self.noise_mkt_close = historical_date + pd.to_timedelta("16:00:00")

        if self.debug:
            self.output_debug("初始化仿真器")

    def output_debug(self,message):
        print(f"DEBUG: {message}")
        print(f"市场开盘时间: {self.mkt_open}")
        print(f"市场收盘时间: {self.mkt_close}")
        print(f"历史数据流长度: {self.stream_history_length}")
        print(f"日志目录: {self.log_dir}")
        print(f"详细输出: {self.verbose}")
        print(f"交易所记录订单日志: {self.exchange_log_orders}")
        print(f"订单簿更新频率: {self.book_freq}")

        
        