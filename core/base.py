from __future__ import annotations
from ast import Raise
import numpy as np


# class Singleton:
#     _instances = {}

#     def __new__(cls, *args, **kwargs):
#         if cls not in cls._instances:
#             instance = super(Singleton, cls).__new__(cls)
#             instance.__init__(*args, **kwargs)
#             instance._initialized = True
#             cls._instances[cls] = instance

#         return cls._instances[cls]


class Singleton(type):
    """
    This is a thread-safe implementation of Singleton.
    """

    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]


class Trackable:
    _subclass_instances = {}

    def __init__(self, *args, **kwargs):
        cls = self.__class__
        if cls not in Trackable._subclass_instances:
            Trackable._subclass_instances[cls] = []
        self.id = len(Trackable._subclass_instances[cls])
        Trackable._subclass_instances[cls].append(self)

    @classmethod
    def get_instance_by_id(cls, id_: int):
        instances = Trackable._subclass_instances.get(cls, [])
        if id_ < len(instances):
            return instances[id_]
        else:
            raise ValueError(
                f"Instance with ID {id_} does not exist in {cls.__name__}."
            )

    @classmethod
    def reset_all_instances(cls):
        cls._subclass_instances.clear()

    def __lt__(self, other: Trackable) -> bool:
        if not type(self) is type(other):
            raise TypeError("Cannot compare instances of different classes.")
        return self.id < other.id

    @classmethod
    def __class_getitem__(cls, id_: int):
        return cls.get_instance_by_id(id_)

    @staticmethod
    def size(cls):
        """
        Returns the number of instances of this class.
        """
        return len(Trackable._subclass_instances.get(cls, []))


class RandomState(metaclass=Singleton):
    def __init__(self, seed: int = 1234):
        self.seed = seed
        self.state = np.random.RandomState(self.seed)

    def reset(self):
        self.state = np.random.RandomState(self.seed)
        return self.state


class Handler:
    _handlers = {}

    @classmethod
    def register_handler(cls, type_):
        def wrapper(handler):
            cls._handlers[type_] = handler
            return handler

        return wrapper

    def get_handler(self, type_):
        handler = self._handlers.get(type_)
        if handler:
            return handler
        else:
            raise ValueError(f"No handler registered for type {type_}.")
