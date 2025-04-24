from core.kernel import Kernel
from core.symbol import Symbol
import pytest
from agent import Agent, TradingAgent
from core.exchange import Exchange


@pytest.fixture
def kernel():
    log_path = "result/test_kernel/test_kernel.log"
    # 清空测试日志文件
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("")

    # 创建一个 Kernel 实例
    kernel = Kernel(config_path="./tests/data/config/test.json")
    return kernel


def test_kernel_initialization(kernel):
    # 测试 Kernel 的初始化
    assert kernel is not None, "Kernel should be initialized"
    assert kernel.cm is not None, "Kernel config should be loaded"
    assert kernel.clock is not None, "Kernel time should be initialized"
    assert kernel.symbol_config is not None, "Kernel current time should be initialized"


def test_symbol_config(kernel):
    assert Symbol["SYM1"] is not None, "Symbol SYS1 should be initialized"
    assert Symbol["SYM2"] is not None, "Symbol SYS2 should be initialized"


def test_agent_config(kernel):

    assert kernel.agent_config is not None, "Agent config should be loaded"
    assert Agent.size() == 10, "There should be 5 agents initialized"
    assert Agent[0].id == 0, "First agent should have ID 0"
    assert Agent[1].agent_id == 1, "1st agent should have ID 1"
    # assert Agent[100].id == 100, "101st agent should have ID 100"
    assert TradingAgent[5].agent_id == 5, "First trading agent should have ID 0"
    # assert TradingAgent[0].agent_id == 5, "0st trading agent should have ID 5"
    assert TradingAgent.size() == 10, "There should be 5 trading agents initialized"
    # assert (
    #     Agent[5] is TradingAgent[0]
    # ), "First trading agent should be the same as first agent"
    assert isinstance(
        Agent[5], TradingAgent
    ), "First trading agent should be the same as first agent"

    assert (
        Agent[0] is TradingAgent[0]
    ), "First agent should be the same as first trading agent"


def test_exchange_config(kernel):
    assert kernel.exchange_config is not None, "Exchange config should be loaded"
    assert (
        kernel.exchange_config.name == "Exchange"
    ), "Exchange name should be 'Exchange'"
    assert kernel.exchange is Exchange(), "Exchange instance should be initialized"


def test_kernel_start(kernel):
    # 测试 Kernel 的启动
    kernel.start()
