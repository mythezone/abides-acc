from __future__ import annotations

from typing import Iterable, Sequence

from core.message import Message, MessageType

from .base import BaseHandler


class MethodHandler(BaseHandler):
    """Routes the message to a method on the exchange instance."""

    message_types: Sequence[MessageType]

    def __init__(self, message_types: Iterable[MessageType], method_name: str) -> None:
        if not isinstance(message_types, Sequence):
            message_types = tuple(message_types)
        self.message_types = tuple(message_types)
        super().__init__()
        self.method_name = method_name

    def handle(self, exchange, message: Message, now):
        method = getattr(exchange, self.method_name)
        return method(message, now)
