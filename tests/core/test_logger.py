import logging
import pytest
from core.logger import Logger  # 根据你的文件结构调整导入路径
import os


@pytest.fixture
def logger():
    # 使用 pytest 的 tmpdir 来创建临时日志文件
    log_file = "./tests/core/logger.log"
    logger = Logger(log_file)
    return logger, log_file


def test_singleton_logger(logger):
    # 获取 logger 实例
    logger_instance_1, _ = logger
    logger_instance_2 = Logger("./tests/core/logger.log")

    # 确保两个实例是相同的（单例）
    assert logger_instance_1 is logger_instance_2, "Logger should be a singleton"


def test_log_writing(logger):
    # 获取 logger 实例和日志文件路径
    logger_instance, log_file = logger

    # 写入一条日志
    logger_instance.exchange_log("这是测试日志")

    # 读取日志文件内容
    with open(log_file, "r", encoding="utf-8") as file:
        log_content = file.read()

    # 检查日志内容是否符合预期
    assert (
        "这是测试日志" in log_content
    ), "Log content should include the expected log message"
    assert "Exchange" in log_content, "Log should contain the logger's name"
    assert "INFO" in log_content, "Log should have the INFO level"


def test_log_multiple_entries(logger):
    # 获取 logger 实例和日志文件路径
    logger_instance, log_file = logger

    # 写入多条日志

    logger_instance.exchange_log("第一条日志")
    logger_instance.exchange_log("第二条日志")

    # 读取日志文件内容
    with open(log_file, "r", encoding="utf-8") as file:
        log_content = file.read()

    # 检查是否包含多条日志
    assert "第一条日志" in log_content, "First log entry should be in the log file"
    assert "第二条日志" in log_content, "Second log entry should be in the log file"


def test_log_file_exists(logger):
    # 获取 logger 实例和日志文件路径
    logger_instance, log_file = logger
    logger_instance.exchange_log("测试日志")  # 写入一条日志

    # 确保日志文件存在
    assert os.path.exists(log_file), "Log file should exist after logging"
