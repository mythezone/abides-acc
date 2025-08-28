from pydantic import BaseModel, Field


class KlineItem(BaseModel):
    """
    Represents a single Kline item with its attributes.
    """

    timestamp: int
    open: float
    close: float
    high: float
    low: float
    volume: int
