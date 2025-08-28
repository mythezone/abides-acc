from unittest.mock import Base
from pydantic import BaseModel, Field


class DepthItem(BaseModel):
    """
    Represents a single Depth item with its attributes.
    """

    price: float
    amount: int
