from dataclasses import dataclass
from typing import Optional


@dataclass
class Order:
    agent_id: str
    timestamp: str
    side: str  # 'buy' or 'sell'
    quantity: int

    @classmethod
    def from_dict(cls, data: dict):
        order_type = data.get("type", "limit")
        if order_type == "market":
            return MarketOrder(
                agent_id=data["agent_id"],
                timestamp=data["timestamp"],
                side=data["side"],
                quantity=data["quantity"],
            )
        else:
            return LimitOrder(
                agent_id=data["agent_id"],
                timestamp=data["timestamp"],
                side=data["side"],
                quantity=data["quantity"],
                price=data["price"],
            )


@dataclass
class LimitOrder(Order):
    price: float


@dataclass
class MarketOrder(Order):
    pass
