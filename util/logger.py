# util/logger_process.py
import time
import datetime
import os
import pandas as pd 


class Logger:
    _instance = None

    def __new__(cls,*args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    

    def __init__(self, log_file:str='logs/simulation.log'):
        if self._initialized:
            return
        self.messages = []
        self.log_file = log_file
        if not os.path.exists(self.log_file):
            os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        self._initialized = True


    def log(self, message:str, current_time:pd.Timestamp=None):
        if current_time is None:
            current_time = pd.Timestamp.now()
        timestamp = current_time.to_pydatetime().strftime('%Y-%m-%d %H:%M:%S.%f ')
        log_message = f"{timestamp} - {message}\n"
        self.messages.append(log_message)

    def dump(self):
        with open(self.log_file, 'a') as f:
            for message in self.messages:
                f.write(message)
        self.messages = []



