import unittest
from util.base import Trackable


class DummyClass(Trackable):
    def __init__(self, name):
        super().__init__()
        self.name = name

    def __str__(self):
        return f"DummyClass(name={self.name}, id={self.id})"
    
class DummyClass2(Trackable):
    def __init__(self, name):
        super().__init__()
        self.name = name

    def __str__(self):
        return f"DummyClass2(name={self.name}, id={self.id})"
    

class TestTrackable(unittest.TestCase):
    def setUp(self):
        Trackable._subclass_instances.clear()
        self.instance1 = DummyClass("Instance 1")
        self.instance2 = DummyClass("Instance 2")
        self.instance3 = DummyClass2("Instance 2-1")
        self.instance4 = DummyClass2("Instance 2-2")



    def test_id_assignment(self):
        self.assertEqual(self.instance1.id, 0)
        self.assertEqual(self.instance2.id, 1)
        self.assertEqual(self.instance3.id, 0) 
        self.assertEqual(self.instance4.id, 1)

         # Different class, same ID
        self.assertEqual(DummyClass.get_instance_by_id(0), self.instance1)
        self.assertEqual(DummyClass.get_instance_by_id(1), self.instance2)
        self.assertEqual(DummyClass2.get_instance_by_id(0), self.instance3)
        self.assertRaises(ValueError, DummyClass.get_instance_by_id, 5)
        self.assertRaises(ValueError, DummyClass2.get_instance_by_id, 6)

    def test_lt(self):
        self.assertTrue(self.instance1 < self.instance2)
        self.assertFalse(self.instance2 < self.instance1)
        self.assertTrue(self.instance3 < self.instance4)
        self.assertFalse(self.instance4 < self.instance3)

        # Different classes should raise TypeError
        with self.assertRaises(TypeError):
            _ = self.instance1 < self.instance3
        with self.assertRaises(TypeError):
            _ = self.instance3 < self.instance1

    def test_class_getitem(self):
        self.assertEqual(DummyClass[0], self.instance1)
        self.assertEqual(DummyClass[1], self.instance2)
        self.assertEqual(DummyClass2[0], self.instance3)
        self.assertEqual(DummyClass2[1], self.instance4)

        # Test invalid ID
        with self.assertRaises(ValueError):
            _ = DummyClass[5]
        with self.assertRaises(ValueError):
            _ = DummyClass2[6]