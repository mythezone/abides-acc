import logging
from core.base import Singleton


class Logger(metaclass=Singleton):
    def __init__(self):
        self.exchange = logging.getLogger("exchange")
        self.getLogger = logging.getLogger
        self.logging = logging

    @staticmethod
    def logging():
        return logging

    @staticmethod
    def getLogger(name):
        return logging.getLogger(name)
