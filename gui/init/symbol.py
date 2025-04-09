import numpy as np 


class Symbol:
    def __init__(self, 
                 name, 
                 r_bar, 
                 kappa: 1.67e-16,
                 sigma_s: 0,
                 fund_vol:1e-8,
                 megashock_lambda_a: 2.77778e-18,
                 megashock_mean: 1e3,
                 megashock_var: 5e4,
    ):
        self.name = name
        self.r_bar = r_bar
        self.kappa = kappa
        self.sigma_s = sigma_s
        self.fund_vol = fund_vol
        self.megashock_lambda_a = megashock_lambda_a
        self.megashock_mean = megashock_mean
        self.megashock_var = megashock_var


class Symbols:
    def __init__(self,debug=True):
        self.debug = debug
        self.symbols = []
        self.symbols_name = []

    def add_symbol(self, name,r_bar, kappa,sigma_s, fund_vol, megashock_lambda_a, megashock_mean, megashock_var):
        if name in self.symbols_name:
            return 
        self.symbols_name.append(name)
        symbol = Symbol(
            name=name,
            r_bar=r_bar,
            kappa=kappa,
            sigma_s=sigma_s,
            fund_vol=fund_vol,
            megashock_lambda_a=megashock_lambda_a,
            megashock_mean=megashock_mean,
            megashock_var=megashock_var
        )
        self.symbols.append(symbol)
        if self.debug:
            self.show_debug("添加股票成功") 

    def show_debug(self,message):
        print(f"DEBUG: {message}")
        for symbol in self.symbols:
            print(f"股票名称: {symbol.name}")
            print(f"R_bar: {symbol.r_bar}")
            print(f"Kappa: {symbol.kappa}")
            print(f"Sigma_s: {symbol.sigma_s}")
            print(f"基础波动率: {symbol.fund_vol}")
            print(f"Megashock_lambda_a: {symbol.megashock_lambda_a}")
            print(f"Megashock_mean: {symbol.megashock_mean}")
            print(f"Megashock_var: {symbol.megashock_var}")
        print("股票列表:")
        for symbol in self.symbols:
            print(symbol.name,end=" ")
        print("股票数量:",end=" ")
        print(len(self.symbols))
        print("股票名称数量:",end=" ")
        print(len(self.symbols_name))




