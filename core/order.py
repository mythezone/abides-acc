from dataclasses import dataclass, field
from typing import Optional
import itertools
import random
import time

_order_id_gen = itertools.count(1)


@dataclass
class Order:
    agent_id: str
    timestamp: str
    side: str  # 'buy' or 'sell'
    quantity: int
    stock: str = ""
    id: int = field(default_factory=lambda: next(_order_id_gen))

    @classmethod
    def from_dict(cls, data: dict) -> "Order":
        stock = data.get("stock") or data.get("_stock") or ""
        return cls(
            agent_id=data["agent_id"],
            timestamp=data["timestamp"],
            side=data["side"],
            quantity=data["quantity"],
            stock=stock,
            id=data.get("id", next(_order_id_gen)),
        )


@dataclass
class LimitOrder(Order):
    price: float = field(default=0.0)

    @classmethod
    def from_dict(cls, data: dict) -> "LimitOrder":
        return cls(
            agent_id=data["agent_id"],
            timestamp=data["timestamp"],
            side=data["side"],
            quantity=data["quantity"],
            price=data["price"],
            stock=data.get("stock") or data.get("_stock") or "",
            id=data.get("id", next(_order_id_gen)),
        )


@dataclass
class MarketOrder(Order):
    market_depth: Optional[int] = None

    @classmethod
    def from_dict(cls, data: dict) -> "MarketOrder":
        return cls(
            agent_id=data["agent_id"],
            timestamp=data["timestamp"],
            side=data["side"],
            quantity=data["quantity"],
            stock=data.get("stock") or data.get("_stock") or "",
            id=data.get("id", next(_order_id_gen)),
            market_depth=data.get("market_depth"),
        )


def generate_random_order(stock: str) -> Order:
    order_type = random.choice(["limit", "market"])
    side = random.choice(["buy", "sell"])
    quantity = random.randint(1, 1000)
    price = round(random.uniform(10, 500), 2)
    timestamp = str(time.time())
    agent_id = f"agent_{random.randint(1, 100)}"

    if order_type == "limit":
        return LimitOrder(
            agent_id=agent_id,
            stock=stock,
            timestamp=timestamp,
            side=side,
            quantity=quantity,
            price=price,
        )
    else:
        return MarketOrder(
            agent_id=agent_id,
            stock=stock,
            timestamp=timestamp,
            side=side,
            quantity=quantity
        )
