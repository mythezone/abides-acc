"""Compatibility layer re-exporting the new order book implementation."""

from core.orderbook import LimitOrderBook

__all__ = ["LimitOrderBook"]
