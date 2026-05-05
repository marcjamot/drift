from __future__ import annotations

from typing import Any, Generic, TypeVar

T = TypeVar("T")


class PerMinion(Generic[T]):
    """Marker: field is keyed per minion instance_id. Always pass a Minion as subject."""


class PerPlayer(Generic[T]):
    """Marker: field is keyed per player_id. Always pass a PlayerState as subject."""


class MatchScope:
    """Base for match-wide memory schemas.

    Fields persist for the full match across all state transitions.
    Declare fields as typed class attributes::

        class MatchMemory(MatchScope):
            divine_shield: PerMinion[bool] = False   # per-minion flag
            total_broken: int = 0                    # match-global counter
    """


class StateScope:
    """Base for state-scoped memory schemas.

    Fields are automatically cleared on every state transition.
    Use for transient counters and flags that reset each round::

        class StateMemory(StateScope):
            shields_broken_this_round: int = 0
    """


def _build_prefix(addon_id: str, scope: str, subject: Any) -> str:
    """Build the store key prefix for a given addon, scope, and optional subject.

    Key conventions:
        match + Minion   →  minion:{id}:           (matches existing card on_state writes)
        match + Player   →  player:{pid}:{addon}:
        match  global    →  {addon}:
        state + Minion   →  _state:minion:{id}:
        state + Player   →  _state:player:{pid}:{addon}:
        state  global    →  _state:{addon}:
    """
    from .models.card import Minion
    from .models.player import PlayerState

    if scope == "match":
        if isinstance(subject, Minion):
            return f"minion:{subject.instance_id}:"
        if isinstance(subject, PlayerState):
            return f"player:{subject.player_id}:{addon_id}:"
        return f"{addon_id}:"

    # state scope — all keys start with "_state:" for bulk clearing on transition
    if isinstance(subject, Minion):
        return f"_state:minion:{subject.instance_id}:"
    if isinstance(subject, PlayerState):
        return f"_state:player:{subject.player_id}:{addon_id}:"
    return f"_state:{addon_id}:"


class MemoryProxy:
    """Typed read/write proxy for addon memory backed by the engine store.

    Obtained via ``ctx.memory_match(self, subject?)`` or ``ctx.memory_state(self, subject?)``.

    - Read:  ``proxy.field``         — reads from the store at the computed key.
    - Write: ``proxy.field = value`` — writes to the store immediately and queues
             a delta that the next ``ctx.emit()`` flushes into the replay log.

    Cross-addon proxies (obtained by passing another addon's class) are read-only.
    """

    def __init__(
        self,
        store: Any,
        prefix: str,
        schema: type,
        pending: dict[str, Any],
        *,
        readonly: bool = False,
    ) -> None:
        object.__setattr__(self, "_store", store)
        object.__setattr__(self, "_prefix", prefix)
        object.__setattr__(self, "_schema", schema)
        object.__setattr__(self, "_pending", pending)
        object.__setattr__(self, "_readonly", readonly)

    def _annotations(self) -> dict[str, Any]:
        schema: type = object.__getattribute__(self, "_schema")
        result: dict[str, Any] = {}
        for base in reversed(schema.__mro__):
            result.update(getattr(base, "__annotations__", {}))
        return result

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        store: Any = object.__getattribute__(self, "_store")
        prefix: str = object.__getattribute__(self, "_prefix")
        schema: type = object.__getattribute__(self, "_schema")

        annotations = self._annotations()
        if name not in annotations:
            raise AttributeError(f"{schema.__name__} has no field '{name}'")
        default = getattr(schema, name, None)
        return store.get(f"{prefix}{name}", default)

    def __setattr__(self, name: str, value: Any) -> None:
        readonly: bool = object.__getattribute__(self, "_readonly")
        if readonly:
            raise AttributeError("cross-addon memory is read-only")

        schema: type = object.__getattribute__(self, "_schema")
        annotations = self._annotations()
        if name not in annotations:
            raise AttributeError(f"{schema.__name__} has no field '{name}'")

        store: Any = object.__getattribute__(self, "_store")
        prefix: str = object.__getattribute__(self, "_prefix")
        pending: dict[str, Any] = object.__getattribute__(self, "_pending")

        key = f"{prefix}{name}"
        store._set(key, value)
        pending[key] = value
