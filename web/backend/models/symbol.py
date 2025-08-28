from typing import List
from .kline import KlineItem
from .depth import DepthItem
from pydantic import BaseModel, Field


class SymbolKlineBlock(BaseModel):
    realKline: List[KlineItem]
    realBids: List[DepthItem]
    realAsks: List[DepthItem]
    simKline: List[KlineItem]
    simBids: List[DepthItem]
    simAsks: List[DepthItem]
