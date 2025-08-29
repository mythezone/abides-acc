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
        self.log_file = os.path.join(self.log_folder, "log.csv")

        with open(self.log_file, "w") as file:
            file.write("time,stage,type,sender,recipient,content\n")

        self.loggers = {
            "exchange": logging.getLogger("Exchange"),
            "lob": logging.getLogger("LOB"),
            "kernel": logging.getLogger("Kernel"),
            "ohlc": logging.getLogger("OHLC"),
            "agents": logging.getLogger("Agents"),
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
                # CSV formatted message flow log
                formatter = logging.Formatter(
                    "%(recive_time)s,%(stage)s,%(mtype_name)s,%(sender_id)s,%(recipient_id)s,%(msg)s"
                )
                h = MemoryHandler()
                h.setFormatter(formatter)
                logger.addHandler(h)
                logger.setLevel(logging.INFO)
                self._handlers.append(h)
            elif logger_name == "ohlc":
                # placeholder (we write OHLC per symbol directly)
                h = MemoryHandler()
                h.setFormatter(logging.Formatter("%(message)s"))
                logger.addHandler(h)
                logger.setLevel(logging.INFO)
                self._handlers.append(h)

            elif logger_name == "lob":
                # placeholder (we write LOB per symbol directly)
                h = MemoryHandler()
                h.setFormatter(logging.Formatter("%(message)s"))
                logger.addHandler(h)
                logger.setLevel(logging.INFO)
                self._handlers.append(h)
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

    def _ensure_symbol_paths(self, symbol_name: str):
        sdir = os.path.join(self.log_folder, symbol_name)
        os.makedirs(sdir, exist_ok=True)
        ohlc_path = os.path.join(sdir, "ohlc.csv")
        lob_path = os.path.join(sdir, "lob.csv")
        if not os.path.exists(ohlc_path):
            with open(ohlc_path, "w") as f:
                f.write("kernel_time,open,high,low,close,volume\n")
        if not os.path.exists(lob_path):
            with open(lob_path, "w") as f:
                # Default header for 5 levels; caller should keep consistent
                f.write(self.format_lob_header(level=5))
        return ohlc_path, lob_path

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
        ohlc_path, _ = self._ensure_symbol_paths(symbol_name)
        with open(ohlc_path, "a") as f:
            line = (
                f"{self.iso_time_format(kernel_time)},{open_:.2f},{high:.2f},{low:.2f},{close:.2f},{int(volume)}\n"
            )
            f.write(line)

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
        try:
            import json
            msg = json.dumps(message.content, ensure_ascii=False, separators=(",", ":"))
        except Exception:
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
        _, lob_path = self._ensure_symbol_paths(symbol_name)
        # If level differs from default header, rewrite header once (simple approach)
        if os.path.getsize(lob_path) == 0:
            with open(lob_path, "w") as f:
                f.write(self.format_lob_header(level=level))
        with open(lob_path, "a") as f:
            f.write(f"{self.iso_time_format(kernel_time)},{lob}\n")

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
        # save all handlers to the primary log file (message flow)
        with open(self.log_file, "a") as file:
            for h in self._handlers:
                if isinstance(h, MemoryHandler):
                    file.write(h.get_logs())
                    h.clear_logs()

    def _ensure_agent_path(self, agent_id: str) -> str:
        adir = os.path.join(self.log_folder, "agents")
        os.makedirs(adir, exist_ok=True)
        apath = os.path.join(adir, f"{agent_id}.csv")
        if not os.path.exists(apath) or os.path.getsize(apath) == 0:
            with open(apath, "w") as f:
                f.write("time,cash,total_value,positions\n")
        return apath

    def agent_log(self, agent_id: str, kernel_time: Union[str, pd.Timestamp], cash: float, total_value: float, positions: dict):
        apath = self._ensure_agent_path(agent_id)
        try:
            import json
            pos_str = json.dumps(positions, ensure_ascii=False, separators=(",", ":"))
        except Exception:
            pos_str = str(positions)
        with open(apath, "a") as f:
            f.write(
                f"{self.iso_time_format(kernel_time)},{cash:.2f},{total_value:.2f},{pos_str}\n"
            )

    @staticmethod
    def format_lob_header(level: int = 5):
        lob_header = "kernel_time,"
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
