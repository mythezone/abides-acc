from __future__ import annotations

from typing import Iterable, Sequence

from core.message import Message, MessageType


class BaseHandler:
    """Interface for exchange message handlers."""

    message_types: Sequence[MessageType] = ()

    def __init__(self) -> None:
        if not isinstance(self.message_types, Iterable) or not self.message_types:
            raise ValueError("Handler must declare at least one message type")

    def handle(self, exchange, message: Message, now):
        raise NotImplementedError
