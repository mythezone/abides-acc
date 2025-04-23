import logging
from core.base import Singleton


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
        }

        # 使用自定义的同步文件 Handler
        exchange_handler = FileHandler(filename)
        exchange_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        self.loggers["exchange"].addHandler(exchange_handler)
        self.loggers["exchange"].setLevel(logging.INFO)

    def exchange_log(self, message: str):
        """
        记录交易所日志。
        """
        self.loggers["exchange"].info(message)
