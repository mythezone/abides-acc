import unittest
from core.clock import Clock


class TestClock(unittest.TestCase):
    def test_initialization(self):
        Clock.__annotations__.clear()
        self.clock = Clock("2018-10-18 09:30:00")
        self.assertEqual(self.clock.current_time.isoformat(), "2018-10-18T09:30:00")

    def test_tick(self):
        clock = Clock()
        clock.tick(nanoseconds=1_000_000_000)  # 1秒
        self.assertEqual(clock.current_time.isoformat(), "2018-10-18T09:30:01")

    def test_tick_to(self):
        clock = Clock()
        clock.tick_to("2018-10-18 09:31")
        self.assertEqual(clock.current_time.isoformat(), "2018-10-18T09:31:00")

    def test_get_time(self):
        clock = Clock()
        clock.tick_to("2018-10-18 09:30")
        t1 = clock.future(hours=1, minutes=30, seconds=15)
        self.assertEqual(t1.isoformat(), "2018-10-18T11:00:15")
