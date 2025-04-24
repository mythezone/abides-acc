import logging
from core.base import Singleton
import pandas as pd
from core.message import Message


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

    def __init__(self, filename: str):
        self.loggers = {
            "exchange": logging.getLogger("Exchange"),
            "order": logging.getLogger("Order"),
            "msg": logging.getLogger("Msg"),
            "kernel": logging.getLogger("Kernel"),
            "agent": logging.getLogger("Agent"),
        }

        # 使用自定义的同步文件 Handler
        exchange_handler = FileHandler(filename)
        exchange_handler.setFormatter(
            logging.Formatter("%(kernel_time)s - %(name)s - %(type_)s - %(message)s")
        )
        self.loggers["exchange"].addHandler(exchange_handler)
        self.loggers["exchange"].setLevel(logging.INFO)

        # 设置kernel的handler
        kernel_handler = FileHandler(filename)
        kernel_handler.setFormatter(
            logging.Formatter(
                "%(recive_time)s - %(mtype_name)s - Agent %(sender_id)s - %(msg)s"
            )
        )
        self.loggers["kernel"].addHandler(kernel_handler)
        self.loggers["kernel"].setLevel(logging.INFO)

        agent_handler = FileHandler(filename)
        self.loggers["agent"].addHandler(agent_handler)
        self.loggers["agent"].setLevel(logging.INFO)
        self.agent_log = self.kernel_log

    def exchange_log(
        self, message: str, kernel_time: str | pd.Timestamp, type_: str = "INIT"
    ):
        """
        记录交易所日志。
        """

        self.loggers["exchange"].info(
            message,
            extra={"kernel_time": self.iso_time_format(kernel_time), "type_": type_},
        )

    def kernel_log(self, message: Message):
        """
        记录内核日志。
        """
        msg = str(message.content)
        self.loggers["kernel"].info(
            msg,
            extra={
                "recive_time": self.iso_time_format(message.recive_time),
                "mtype_name": message.message_type.name,
                "sender_id": message.sender_id,
            },
        )

    @staticmethod
    def iso_time_format(time: str | pd.Timestamp) -> str:
        """
        格式化时间戳为 ISO 格式。
        """
        if isinstance(time, pd.Timestamp):
            return time.strftime("%Y-%m-%dT%H:%M:%S.%f")
        else:
            return time
