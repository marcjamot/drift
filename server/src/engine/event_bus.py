from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Callable, DefaultDict, Literal, TypeVar

from .events import EventPayload

Phase = Literal["pre", "on", "after"]
P = TypeVar("P")
Callback = Callable[[P], None]


@dataclass(frozen=True)
class _Listener:
    priority: int
    callback: Callback  # type: ignore[type-arg]


class EventBus:
    _PHASES: tuple[Phase, ...] = ("pre", "on", "after")

    def __init__(self) -> None:
        self._listeners: DefaultDict[str, dict[Phase, list[_Listener]]] = defaultdict(
            lambda: {phase: [] for phase in self._PHASES}
        )
        self._wildcard: dict[Phase, list[_Listener]] = {phase: [] for phase in self._PHASES}

    def on(
        self,
        event: str,
        callback: Callable[[EventPayload], None],
        *,
        phase: Phase = "on",
        priority: int = 0,
    ) -> Callable[[EventPayload], None]:
        bucket = self._wildcard if event == "*" else self._listeners[event]
        bucket[phase].append(_Listener(priority=priority, callback=callback))
        bucket[phase].sort(key=lambda listener: listener.priority, reverse=True)
        return callback

    def clear_temporary(self) -> None:
        self._listeners.clear()
        self._wildcard = {phase: [] for phase in self._PHASES}

    def emit(self, payload: object) -> object:
        if hasattr(payload, "event"):
            event = payload.event  # type: ignore[union-attr]
        elif isinstance(payload, dict):
            event = payload.get("event", "")
        else:
            event = ""
        for phase in self._PHASES:
            listeners = [
                *self._listeners.get(event, {}).get(phase, []),
                *self._wildcard.get(phase, []),
            ]
            listeners.sort(key=lambda listener: listener.priority, reverse=True)
            for listener in list(listeners):
                listener.callback(payload)  # type: ignore[arg-type]
        return payload

    def is_self(self, observer: object, subject: object) -> bool:
        return (
            observer is not None
            and subject is not None
            and getattr(observer, "instance_id", None) == getattr(subject, "instance_id", None)
        )
