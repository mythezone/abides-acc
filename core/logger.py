import logging

from joblib import Memory
from core.base import Singleton
import pandas as pd
from core.message import Message
from io import StringIO
import os
from typing import Union


class MemoryHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.memory_log = StringIO()

    def emit(self, record: logging.LogRecord):
        """
        将日志信息写入内存。
        """
        log_entry = self.format(record)
        self.memory_log.write(log_entry + "\n")

    def get_logs(self):
        return self.memory_log.getvalue()

    def clear_logs(self):
        self.memory_log.close()
        self.memory_log = StringIO()


class FileHandler(logging.Handler):
    """
    自定义的日志 Handler，将日志同步写入文件。
    """

    def __init__(self, filename: str, mode="a"):
        super().__init__()
        self.filename = filename
        self.mode = mode

        # 打开文件，保持文件打开状态
        self.file = open(self.filename, mode, buffering=1)

    def emit(self, record: logging.LogRecord):
        """
        同步写入日志的核心方法，写入日志信息到文件。
        """
        log_entry = self.format(record)
        self._write_to_file(log_entry)

    def _write_to_file(self, log_entry: str):
        """将日志同步写入文件"""
        self.file.write(log_entry + "\n")

    def close(self):
        """确保文件在退出时正确关闭"""
        super().close()
        if self.file:
            self.file.close()


class Logger(metaclass=Singleton):
    """
    同步 Logger 类，所有记录会通过同步日志写入文件。
    """

    def __init__(self, log_folder: str, level=5):
        self.log_folder = log_folder
        os.makedirs(self.log_folder, exist_ok=True)
        self.lob_file = os.path.join(self.log_folder, "lob.csv")
        self.log_file = os.path.join(self.log_folder, "log.csv")
        self.ohlc_file = os.path.join(self.log_folder, "ohlc.csv")

        with open(self.log_file, "w") as file:
            file.write("kernel_time,type_,message\n")
        with open(self.ohlc_file, "w") as file:
            file.write("symbol_name,kernel_time,open,high,low,close,volume\n")
        with open(self.lob_file, "w") as file:
            file.write("")

        self.loggers = {
            "exchange": logging.getLogger("Exchange"),
            "lob": logging.getLogger("LOB"),
            "kernel": logging.getLogger("Kernel"),
            "ohlc": logging.getLogger("OHLC"),
        }
        # keep all handlers for flushing
        self._handlers = []

        for logger_name, logger in self.loggers.items():
            if logger_name == "exchange":
                formatter = logging.Formatter(
                    "%(kernel_time)s - %(name)s - %(type_)s - %(message)s"
                )
                h = MemoryHandler()
                h.setFormatter(formatter)
                logger.addHandler(h)
                logger.setLevel(logging.INFO)
                self._handlers.append(h)
            elif logger_name == "kernel":
                # Detailed message flow log: time, stage, type, sender->recipient, content
                formatter = logging.Formatter(
                    "%(recive_time)s - %(stage)s - %(mtype_name)s - from %(sender_id)s to %(recipient_id)s - %(msg)s"
                )
                h = MemoryHandler()
                h.setFormatter(formatter)
                logger.addHandler(h)
                logger.setLevel(logging.INFO)
                self._handlers.append(h)
            elif logger_name == "ohlc":
                self.ohlc_handler = MemoryHandler()
                formatter = logging.Formatter(
                    "%(symbol_name)s,%(kernel_time)s,%(open)s,%(high)s,%(low)s,%(close)s,%(volume)s"
                )
                self.ohlc_handler.setFormatter(formatter)
                logger.addHandler(self.ohlc_handler)
                logger.setLevel(logging.INFO)
                self._handlers.append(self.ohlc_handler)

            elif logger_name == "lob":
                self.lob_handler = MemoryHandler()
                formatter = logging.Formatter(
                    "%(symbol_name)s,%(kernel_time)s,%(level)s,%(lob)s"
                )
                self.lob_handler.setFormatter(formatter)
                logger.addHandler(self.lob_handler)
                logger.setLevel(logging.INFO)
                self._handlers.append(self.lob_handler)
            else:
                # default
                formatter = logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                )
                h = MemoryHandler()
                h.setFormatter(formatter)
                logger.addHandler(h)
                logger.setLevel(logging.INFO)
                self._handlers.append(h)

    def ohlc_log(
        self,
        symbol_name: str,
        kernel_time: Union[str, pd.Timestamp],
        open_: float,
        high: float,
        low: float,
        close: float,
        volume: float,
    ):
        """
        记录 OrderBook 日志。
        """
        self.loggers["orderbook"].info(
            "",
            extra={
                "symbol_name": symbol_name,
                "kernel_time": self.iso_time_format(kernel_time),
                "open": open_,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
            },
        )

    def exchange_log(
        self, message: str, kernel_time: Union[str, pd.Timestamp], type_: str = "INIT"
    ):
        """
        记录交易所日志。
        """

        self.loggers["exchange"].info(
            message,
            extra={"kernel_time": self.iso_time_format(kernel_time), "type_": type_},
        )

    def kernel_log(self, message: Message):
        """兼容旧接口：仅记录消息接收。"""
        self.kernel_message_log(message, stage="RECV")

    def kernel_message_log(self, message: Message, stage: str = "RECV"):
        """
        记录一条消息的流转日志。
        stage: SEND | RECV | PROC 等
        """
        msg = str(message.content)
        self.loggers["kernel"].info(
            msg,
            extra={
                "recive_time": self.iso_time_format(message.recive_time),
                "mtype_name": message.message_type.name,
                "sender_id": message.sender_id,
                "recipient_id": getattr(message, "recipient_id", "-"),
                "stage": stage,
            },
        )

    def lob_log(
        self, symbol_name: str, kernel_time: Union[str, pd.Timestamp], level: int, lob: str
    ):
        """
        记录 LOB 日志。
        """
        self.loggers["lob"].info(
            "",
            extra={
                "symbol_name": symbol_name,
                "kernel_time": self.iso_time_format(kernel_time),
                "level": level,
                "lob": lob,
            },
        )

    @staticmethod
    def iso_time_format(time: Union[str, pd.Timestamp]) -> str:
        """
        格式化时间戳为 ISO 格式。
        """
        if isinstance(time, pd.Timestamp):
            return time.strftime("%Y-%m-%dT%H:%M:%S.%f")
        else:
            return time

    def save_log_to_file(self):
        """
        将内存中的日志保存到文件。
        """
        # save all handlers to the primary log file
        with open(self.log_file, "a") as file:
            for h in self._handlers:
                if isinstance(h, MemoryHandler):
                    file.write(h.get_logs())
                    h.clear_logs()

    @staticmethod
    def format_lob_header(level: int = 5):
        lob_header = "symbol_name,kernel_time,"
        for i in range(level):
            lob_header += f"AskPrice{i},"
        for i in range(level):
            lob_header += f"AskVolume{i},"
        for i in range(level):
            lob_header += f"BidPrice{i},"
        for i in range(level):
            if i == level - 1:
                lob_header += f"BidVolume{i}\n"
            else:
                lob_header += f"BidVolume{i},"
        return lob_header
