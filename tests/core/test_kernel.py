from core.kernel import Kernel
from core.symbol import Symbol
import pytest


@pytest.fixture
def kernel():
    # 创建一个 Kernel 实例
    kernel = Kernel(config_path="./tests/data/config/test.json")
    return kernel


def test_kernel_initialization(kernel):
    # 测试 Kernel 的初始化
    assert kernel is not None, "Kernel should be initialized"
    assert kernel.cm is not None, "Kernel config should be loaded"
    assert kernel.clock is not None, "Kernel time should be initialized"
    assert kernel.symbol_args is not None, "Kernel current time should be initialized"


def test_symbol_config(kernel):
    assert Symbol["SYM1"] is not None, "Symbol SYS1 should be initialized"
    assert Symbol["SYM2"] is not None, "Symbol SYS2 should be initialized"
