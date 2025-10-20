from __future__ import annotations

from typing import Dict, List

from core.message import Message, MessageType

from .base import BaseHandler


class HandlerManager:
    def __init__(self) -> None:
        self._handlers: Dict[MessageType, BaseHandler] = {}

    def register(self, handler: BaseHandler) -> None:
        for msg_type in handler.message_types:
            self._handlers[msg_type] = handler

    def handle(self, exchange, message: Message, now) -> List[Message]:
        handler = self._handlers.get(message.message_type)
        if handler is None:
            return []
        return handler.handle(exchange, message, now)
