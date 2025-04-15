import unittest
from core.base import RandomState
import numpy as np


class TestRandomState(unittest.TestCase):
    def setUp(self):
        self.random_state = RandomState(seed=1234)
        state = np.random.RandomState(1234)
        self.y = state.randint(0, 100)

    def test_random_state_initialization(self):
        # self.assertEqual(self.x, self.y)
        self.assertEqual(self.random_state.seed, 1234)
        self.assertEqual(RandomState(1234), self.random_state)

    def test_random_state_set_seed(self):
        s1 = np.random.RandomState(1234)
        s2 = np.random.RandomState(1234)

        x1 = s1.randint(0, 100)
        x2 = s2.randint(0, 100)

        self.assertEqual(x1, x2)

        x3 = self.random_state.state.randint(0, 100)

        self.random_state.reset()
        x4 = self.random_state.state.randint(0, 100)

        self.assertEqual(x3, x4)

        rs = RandomState(1234)
        self.assertEqual(rs, self.random_state)
        rs.reset()
        x5 = rs.state.randint(0, 100)
        self.assertEqual(x4, x5)
