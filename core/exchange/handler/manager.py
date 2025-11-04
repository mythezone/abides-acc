from __future__ import annotations

from typing import Callable, Dict, Iterable, List

from core.message import Message, MessageType

HandlerFunc = Callable[[object, Message, object], List[Message]]

_GLOBAL_REGISTRY: Dict[MessageType, HandlerFunc] = {}
_GLOBAL_SUBTYPE: Dict[str, Dict[str, HandlerFunc]] = {}
_DEFAULT_FIELD = "message_subtype"


def register_handler(*keys, subtype_field: str = _DEFAULT_FIELD):
    def decorator(func: HandlerFunc) -> HandlerFunc:
        if not keys:
            raise ValueError("Handler must register at least one key")
        for key in keys:
            if isinstance(key, MessageType):
                _GLOBAL_REGISTRY[key] = func
            else:
                field_map = _GLOBAL_SUBTYPE.setdefault(subtype_field, {})
                field_map[str(key)] = func
        return func

    return decorator


class HandlerManager:
    def __init__(self) -> None:
        self._handlers: Dict[MessageType, HandlerFunc] = dict(_GLOBAL_REGISTRY)
        self._subtype_handlers: Dict[str, Dict[str, HandlerFunc]] = {
            field: mapping.copy() for field, mapping in _GLOBAL_SUBTYPE.items()
        }

    def register(self, keys: Iterable, handler: HandlerFunc, *, subtype_field: str = _DEFAULT_FIELD) -> None:
        for key in keys:
            if isinstance(key, MessageType):
                self._handlers[key] = handler
            else:
                self._subtype_handlers.setdefault(subtype_field, {})[str(key)] = handler

    def handle(self, exchange, message: Message, now) -> List[Message]:
        handler = self._handlers.get(message.message_type)
        if handler is not None:
            return handler(exchange, message, now)
        content = message.content or {}
        for field, mapping in self._subtype_handlers.items():
            subtype = content.get(field)
            if subtype and subtype in mapping:
                return mapping[subtype](exchange, message, now)
        return []
