import numpy as np
from typing import List
import random


class Symbol:
    _symbol_dict = {}
    _symbol_name_list = []

    def __init__(
        self,
        name: str,
        r_bar: float = 1e5,
        kappa: float = 1.67e-16,
        sigma_s: int = 0,
        fund_vol: float = 1e-8,
        megashock_lambda_a: float = 2.77778e-18,
        megashock_mean: float = 1e3,
        megashock_var: float = 5e4,
    ):

        if name in Symbol._symbol_dict:
            return
        self.name = name
        self.r_bar = r_bar
        self.kappa = kappa
        self.sigma_s = sigma_s
        self.fund_vol = fund_vol
        self.megashock_lambda_a = megashock_lambda_a
        self.megashock_mean = megashock_mean
        self.megashock_var = megashock_var

        Symbol._symbol_dict[name] = self
        Symbol._symbol_name_list.append(name)

    def __str__(self):
        return f"{self.name}: r_bar={self.r_bar}, kappa={self.kappa}, sigma_s={self.sigma_s}, fund_vol={self.fund_vol}, megashock_lambda_a={self.megashock_lambda_a}, megashock_mean={self.megashock_mean}, megashock_var={self.megashock_var}"

    def __repr__(self):
        return f"{self.name}: r_bar={self.r_bar}"

    @classmethod
    def get_symbol_by_name(cls, name):
        if name in cls._symbol_dict:
            return cls._symbol_dict[name]
        else:
            raise ValueError(f"Symbol with name {name} not found.")

    @classmethod
    def __class_getitem__(cls, name):
        return cls.get_symbol_by_name(name)

    @classmethod
    def size(cls):
        return len(cls._symbol_dict)

    @staticmethod
    def get_random_symbol():
        return random.choice(Symbol._symbol_dict.values())

    @staticmethod
    def __len__():
        return len(Symbol._symbol_dict)


class EFT:
    def __init__(self, portfolio: List[Symbol]):
        self.portfolio = portfolio
