import pytest
from core.config import ConfigManager as CM
import multiprocessing


@pytest.fixture
def config():
    cm = CM("./tests/data/config/test.json")
    return cm


def test_singleton_config(config):
    # 获取 config 实例
    config_instance_1 = config
    config_instance_2 = CM()

    # 确保两个实例是相同的（单例）
    assert config_instance_1 is config_instance_2, "ConfigManager should be a singleton"


def test_load_config(config):
    start_at = config.simulation_datetime.start_at
    end_at = config.simulation_datetime.end_at
    assert (
        start_at == "2023-10-01T09:30:00"
    ), "Start time should be '2023-10-01 00:00:00'"
    assert end_at == "2023-10-01T11:30:00", "End time should be '2023-10-31 23:59:59'"


def test_update_attributes(config):
    # 测试更新属性
    config.load_config("./tests/data/config/test2.json")
    assert (
        config.simulation_datetime.start_at == "2023-10-01T09:30:00"
    ), "Start time should be updated to '2023-10-01 09:30:00'"

    assert (
        config.updated_attributes.name == "test2"
    ), "Name should be updated to 'test2'"

    cm2 = CM(
        "example_config.json"
    )  # 第二次初始化不会自动加载配置，需要手动调用load_config更新配置
    assert (
        cm2.updated_attributes.name == "test2"
    ), "Name should be updated to 'test2' in the singleton instance"


# def test_multiprocess_singleton_config(config):
#     # 测试多进程下的单例模式
#     def worker(config_file):
#         cm = CM(config_file)
#         print(cm.simulation_datetime.start_at)

#     process1 = multiprocessing.Process(target=worker, args=("./tests/data/config/test.json",))
#     process2 = multiprocessing.Process(target=worker, args=("./tests/data/config/test_2.json",))
#     process1.start()
#     process2.start()
#     process1.join()
#     process2.join()
