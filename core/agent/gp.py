from core.agent.fundamental import FundamentalTrackingAgent
from core.message import MessageType, MessageQueue, Message, new_message

import numpy as np
import pygad
import random


class GPAgent(FundamentalTrackingAgent):

    def __init__(
        self,
        id,
        *args,
        h=1,  # shares of the stock for each trader
        M_0=1e11,  # initial money supply for each trader, in cents
        r=0.05,
        r_d=0.0002,  # interest rates
        K=52,  # the trading frequency over a year
        D_bar=0.02,  # stochastic process D_t : MEAN
        sigma_D_square=0.004,  # stochastic process D_t : VARIANCE
        delta_h=1,  # amount for each trade
        h_bar=10,  # maximum shares of stock holding
        N_R=50,  # number of rounds for each period
        N_p=20000,  # number of periods
        N=100,  # number of traders
        N_I=20,  # number of strategies for each trader
        N_T=5,  # tournament size
        N_EC=5,  # evolutionary cycle
        _lambda_=0.5,
        theta_0=0.5,
        omega=15,
        theta_1=0.01,
        theta_2=0.001,
        random_state=None,
        starting_cash=100000,
        initial_symbols=None,
        **kwargs,
    ):
        super().__init__(id, *args, initial_symbols=initial_symbols, **kwargs)
        self.h = h
        self.M_0 = M_0
        self.r = r
        self.r_d = r_d
        self.K = K
        self.D_bar = D_bar
        self.sigma_D_square = sigma_D_square
        self.delta_h = delta_h
        self.h_bar = h_bar
        self.N_R = N_R
        self.N_p = N_p
        self.N = N
        self.N_I = N_I
        self.N_T = N_T
        self.N_EC = N_EC
        self._lambda_ = _lambda_
        self.theta_0 = theta_0
        self.omega = omega
        self.theta_1 = theta_1
        self.theta_2 = theta_2
        # the return rate
        self.R = 1 + self.r / self.K

        self.selected_symbols = list(
            np.random.choice(
                initial_symbols, int(np.random.randint(1, 3)), replace=False
            )
        )

        # expectation array and variance array
        self.expectations = {}
        self.variances = {}
        # the historical price and dividents
        self.prices = {}
        self.dividends = {}
        # auxiliary u array
        self.u = {}

        for symbol in self.selected_symbols:
            self.prices[symbol] = {}
            self.dividends[symbol] = {}
            self.expectations[symbol] = {}
            self.variances[symbol] = {}
            self.u[symbol] = {}

        # record time step
        self.time_step = 1

        # price to update
        self.price_to_update = None

        # genetic programming related attributes
        self.population_size = self.N_I
        self.tournament_size = self.N_T
        self.evolution_cycles = self.N_EC
        self.num_genes = 11
        self.ga_instance = None
        self.mutation_percent_genes = 20
        self.crossover_probability = 0.7

    def action(self):
        super().action()

        if self.time_step == 1:
            return

        requests = []
        for symbol in self.selected_symbols:
            # 1. get reservation price
            reservation_price = self.get_reservation_price(
                t=self.time_step, symbol=symbol
            )
            # 2. get best bid and bst ask price
            best_bid, best_ask = self.get_best_bid_ask(symbol)
            # 3. make trading decision accordingly
            sigma_square_t = self.variances.get(symbol)[f"{self.time_step}"]
            S = self._lambda_ * sigma_square_t * self.delta_h / (1 + self.r)

            if best_bid is not None and best_ask is not None:
                if reservation_price > best_ask:
                    price = best_ask
                    order = {
                        "type": "market_order",
                        "symbol": symbol,
                        "agent_id": self.id,
                        "timestamp": str(self.current_time),
                        "side": "buy",
                        "quantity": 1,
                    }
                elif reservation_price < best_bid:
                    price = best_bid
                    order = {
                        "type": "market_order",
                        "symbol": symbol,
                        "agent_id": self.id,
                        "timestamp": str(self.current_time),
                        "side": "sell",
                        "quantity": 1,
                    }
                else:
                    if reservation_price < (best_ask + best_bid) / 2:
                        price = np.random.uniform(
                            reservation_price, reservation_price + S
                        )
                        order = {
                            "type": "limit_order",
                            "symbol": symbol,
                            "agent_id": self.id,
                            "timestamp": str(self.current_time),
                            "side": "sell",
                            "quantity": 1,
                            "price": price,
                        }
                    else:
                        price = np.random.uniform(
                            reservation_price - S, reservation_price
                        )
                        order = {
                            "type": "limit_order",
                            "symbol": symbol,
                            "agent_id": self.id,
                            "timestamp": str(self.current_time),
                            "side": "buy",
                            "quantity": 1,
                            "price": price,
                        }
            elif best_bid is not None and best_ask is None:
                if reservation_price > best_ask:
                    order = {
                        "type": "market_order",
                        "symbol": symbol,
                        "agent_id": self.id,
                        "timestamp": str(self.current_time),
                        "side": "buy",
                        "quantity": 1,
                    }
                else:
                    price = np.random.uniform(reservation_price - S, reservation_price)
                    order = {
                        "type": "limit_order",
                        "symbol": symbol,
                        "agent_id": self.id,
                        "timestamp": str(self.current_time),
                        "side": "buy",
                        "quantity": 1,
                        "price": price,
                    }
            elif best_bid is None and best_ask is not None:
                if reservation_price < best_bid:
                    order = {
                        "type": "market_order",
                        "symbol": symbol,
                        "agent_id": self.id,
                        "timestamp": str(self.current_time),
                        "side": "sell",
                        "quantity": 1,
                    }
                else:
                    price = np.random.uniform(reservation_price, reservation_price + S)
                    order = {
                        "type": "limit_order",
                        "symbol": symbol,
                        "agent_id": self.id,
                        "timestamp": str(self.current_time),
                        "side": "buy",
                        "quantity": 1,
                        "price": price,
                    }
            elif best_ask is None and best_ask is None:
                u = np.random.rand()
                if u < 0.5:
                    price = np.random.uniform(reservation_price - S, reservation_price)
                    order = {
                        "type": "limit_order",
                        "symbol": symbol,
                        "agent_id": self.id,
                        "timestamp": str(self.current_time),
                        "side": "buy",
                        "quantity": 1,
                        "price": price,
                    }
                else:
                    price = np.random.uniform(reservation_price, reservation_price + S)
                    order = {
                        "type": "limit_order",
                        "symbol": symbol,
                        "agent_id": self.id,
                        "timestamp": str(self.current_time),
                        "side": "sell",
                        "quantity": 1,
                        "price": price,
                    }
            requests.append(order)

        # update the data
        self.update_prices(self.time_step, symbol=symbol)
        self.update_dividends(self.time_step, symbol=symbol)

        # submit the orders
        if requests:
            msg = new_message(
                message_type=MessageType.SUBMIT_ORDER,
                sender_id=self.id,
                recipient_id="Exchange",
                send_time=self.current_time,
                recive_time=self.current_time,
                content={"requests": requests},
            )
            self.send(msg)

        # time-step increment
        self.time_step += 1

    def get_reservation_price(self, t, symbol):
        expectation = self.get_total_expectation(t, symbol=symbol)
        variance = self.get_variance(t, symbol=symbol)
        h = self.get_h(t, symbol=symbol)
        numerator = expectation - self._lambda_ * h * variance
        return numerator / self.R

    def get_h(self, t, symbol):
        expectation = self.get_total_expectation(t, symbol=symbol)
        variance = self.get_variance(t, symbol=symbol)
        P_t = self.prices.get(symbol)[f"{t}"]
        numerator = expectation - self.R * P_t
        denominator = self._lambda_ * variance
        return numerator / denominator

    def get_total_expectation(self, t, symbol):
        """Return the expectation of the sum of wealth and dividends at time-step t, i.e., E_{i,t}(P_{t+1}+D_{t+1})."""
        if str(t) in self.expectations.get(symbol).keys():
            return self.expectations.get(symbol)[f"{t}"]

        if t <= 1:
            raise ValueError(
                "The time-step for expectation has to be larger than or euqal 2."
            )

        f = self.generate_f(symbol=symbol)
        prev_term = (
            self.prices.get(symbol)[f"{t-1}"] + self.dividends.get(symbol)[f"{t-1}"]
        )
        if f >= 0.0:
            result = prev_term * (
                1 + self.theta_0 * np.tanh(np.log(1 + f) / self.omega)
            )
            self.expectations.get(symbol)[f"{t}"] = result
            return result
        else:
            result = prev_term * (
                1 - self.theta_0 * np.tanh(np.log(-np.abs(-1 + f)) / self.omega)
            )
            self.expectations.get(symbol)[f"{t}"] = result
            return result

    def get_variance(self, t, symbol):
        """Return the variance at time-step t, i.e., sigma^2_{i,t} = V_{i,t}(R_{t+1})."""
        if str(t) in self.variances.get(symbol).keys():
            return self.variances.get(symbol)[f"{t}"]

        if t <= 1:
            raise ValueError(
                "The time-step for sigma_square has to be larger than or euqal 2."
            )

        prev_sigma_square = self.variances[f"{t-1}"]
        P_t = self.prices.get(symbol)[f"{t}"]
        D_t = self.dividends.get(symbol)[f"{t}"]

        if str(t - 1) in self.u.keys():
            u_t_minus_one = self.u.get(symbol)[f"{t-1}"]
        else:
            u_t_minus_two = self.u.get(symbol)[f"{t-2}"]
            u_t_minus_one = (1 - self.theta_1) * u_t_minus_two + self.theta_1 * (
                P_t + D_t
            )
            self.u.get(symbol)[str(t - 1)] = u_t_minus_one

        result = (
            (1 - self.theta_1 - self.theta_2) * prev_sigma_square
            + self.theta_1 * (P_t + D_t - u_t_minus_one)
            + self.theta_2
            * (P_t + D_t - self.get_total_expectation(t - 1, symbol=symbol)) ** 2
        )

        self.variances.get(symbol)[f"{t}"] = result
        return result

    def get_best_bid_ask(self, symbol: str):
        msg = self.build_top_of_book_query(symbols=[symbol])
        self.send(msg)
        msg_in: Message = self.message_queue.get_raw()
        if msg_in.message_type == MessageType.QUERY_TOP_OF_BOOK:
            content = msg_in.content
            return content["best bid"], content["best ask"]

    def update_prices(self, t, symbol):
        if self.price_to_update is not None:
            self.prices.get(symbol)[str(t)] = self.price_to_update
            self.price_to_update = None
        else:
            if t >= 2:
                self.prices.get(symbol)[f"{t}"] = self.prices.get(symbol)[f"{t-1}"]

    def update_dividends(self, t, symbol):
        """Sample from normal distribution with mean=D_bar and variance=sigma_D_square."""
        self.dividends.get(symbol)[str(t)] = np.random.normal(
            loc=self.D_bar, scale=self.sigma_D_square**0.5
        )

    def process_inbox(self):
        super().process_inbox()

        for msg in self.inbox:
            msg: Message
            if msg.message_type == MessageType.QUERY_LAST_TRADE:
                self.price_to_update = msg.content.get("data")

    # methods specifically designed for GP
    def generate_f(self, symbol):
        """Return f at the current time-step."""
        if self.ga_instance is None:
            self.init_ga_instance(symbol=symbol)

        # run the GP algorithm
        self.ga_instance.run()

        # get the solution
        solution, _, _ = self.ga_instance.best_solution()

        P_hist = [self.prices.get(symbol)[f"{self.time_step-i}"] for i in range(1, 6)]
        D_hist = [
            self.dividends.get(symbol)[f"{self.time_step-i}"] for i in range(1, 6)
        ]
        R = self.R
        inputs = np.array(P_hist + D_hist + [R])

        # generate a random GP expression and calculate

        f = np.dot(inputs, solution)
        return f

    def init_ga_instance(self, symbol):
        def fitness_func(solution):
            P_hist = [
                self.prices.get(symbol)[f"{self.time_step-i}"] for i in range(1, 6)
            ]
            D_hist = [
                self.dividends.get(symbol)[f"{self.time_step-i}"] for i in range(1, 6)
            ]
            R = self.R
            inputs = np.array(P_hist + D_hist + [R])
            # Note that here we let the output of the fitness to be LINEAR.
            pred = np.dot(solution, inputs)

            # calculate the error
            target = self.prices.get(symbol)[f"{self.time_step}"]
            error = np.abs(pred - target)

            return np.divide(1, error)

        self.ga_instance = pygad.GA(
            num_generations=self.num_generations,
            num_parents_mating=self.tournament_size,
            fitness_func=fitness_func,
            sol_per_pop=self.population_size,
            num_genes=self.num_genes,
            init_range_low=-1.0,
            init_range_high=1.0,
            mutation_percent_genes=self.mutation_percent_genes,
            crossover_probability=self.crossover_probability,
            mutation_type="random",
            crossover_type="single_point",
        )

        def on_generation(ga):
            num_new = int(0.1 * ga.sol_per_pop)
            for _ in range(num_new):
                new_sol = random.uniform(-1, 1, self.num_genes)
                idx = np.random.randint(0, ga.sol_per_pop - 1)
                ga.population[idx] = new_sol

        self.ga_instance.on_generation = on_generation
