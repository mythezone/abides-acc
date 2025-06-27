from dataclasses import dataclass, field
from typing import Optional
import itertools

_order_id_gen = itertools.count(1)


@dataclass
class Order:
    agent_id: str
    timestamp: str
    side: str  # 'buy' or 'sell'
    quantity: int
    id: int = field(default_factory=lambda: next(_order_id_gen))

    @classmethod
    def from_dict(cls, data: dict) -> "Order":
        return cls(
            agent_id=data["agent_id"],
            timestamp=data["timestamp"],
            side=data["side"],
            quantity=data["quantity"],
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
            id=data.get("id", next(_order_id_gen)),
        )


@dataclass
class MarketOrder(Order):

    @classmethod
    def from_dict(cls, data: dict) -> "MarketOrder":
        return cls(
            agent_id=data["agent_id"],
            timestamp=data["timestamp"],
            side=data["side"],
            quantity=data["quantity"],
            id=data.get("id", next(_order_id_gen)),
        )
