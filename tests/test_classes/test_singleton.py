import unittest

from core.base import Singleton  # 替换为你的路径


# 示例子类
class MySingleton(Singleton):
    def __init__(self):
        if hasattr(self, "_initialized") and self._initialized:
            return
        # self._initialized = True
        self.value = 0


class MySingleton2(Singleton):
    def __init__(self,arg1,arg2):
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._initialized = True
        self.arg1 = arg1
        self.arg2 = arg2

class TestSingletonBase(unittest.TestCase):

    def test_single_instance(self):
        a = MySingleton()
        b = MySingleton()
        self.assertIs(a, b, "MySingleton 应该是单例，两个实例应当是同一个对象")

    def test_shared_state(self):
        a = MySingleton()
        b = MySingleton()
        a.value = 42
        self.assertEqual(b.value, 42, "单例对象应共享状态")

    def test_instance_count(self):
        a = MySingleton()
        b = MySingleton()
        c = MySingleton()
        self.assertEqual(len(Singleton._instances), 1, "只有一个 MySingleton 实例应存在于单例缓存中")

    def test_single_instance2(self,):
        a = MySingleton2(1, 2)
        b = MySingleton2(3, 4)
        self.assertIs(a, b, "MySingleton2 应该是单例，两个实例应当是同一个对象")


if __name__ == '__main__':
    unittest.main()