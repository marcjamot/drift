from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Any, Callable

from .event_bus import EventBus
from .memory import MatchScope, StateScope
from .models import CardDef
from .state_machine import StateInsertion, StateMachine

if TYPE_CHECKING:
    from .context import MatchContext, StateContext


# ---------------------------------------------------------------------------
# Decorator metadata containers
# ---------------------------------------------------------------------------

@dataclass
class _EventMeta:
    event: str
    phase: str
    priority: int
    in_state: type | None


@dataclass
class _StateMeta:
    ctx_type: type | None


@dataclass
class _IntentMeta:
    intent: str
    in_state: type | None


# ---------------------------------------------------------------------------
# Decorators for addon authors
# ---------------------------------------------------------------------------

def on_event(
    event: str,
    *,
    phase: str = "on",
    priority: int = 0,
    in_state: type | None = None,
) -> Callable[[Any], Any]:
    """Mark a method to be registered as an event listener when its state condition matches.

    Args:
        event:    Event name (e.g. "damage", "death", "attack").
        phase:    "pre" | "on" | "after" — when in the event lifecycle to fire.
        priority: Higher values fire first within a phase.
        in_state: Optional StateContext subclass filter.
    """
    def decorator(fn: Any) -> Any:
        fn._addon_event = _EventMeta(event=event, phase=phase, priority=priority, in_state=in_state)
        return fn
    return decorator


def on_state(ctx_type: type | None = None) -> Callable[[Any], Any]:
    """Mark a method to be called once when a matching state is entered.

    The method receives the typed StateContext as its only argument::

        @on_state(CombatStateContext)
        def setup_combat(self, ctx: CombatStateContext) -> None: ...
    """
    def decorator(fn: Any) -> Any:
        fn._addon_state = _StateMeta(ctx_type=ctx_type)
        return fn
    return decorator


def on_intent(
    intent: str,
    *,
    in_state: type | None = None,
) -> Callable[[Any], Any]:
    """Mark a method as an intent handler for inbound client messages.

    The engine routes WS messages with matching ``type`` to this handler.
    Handler receives ``(player_id: str, payload: dict, ctx: StateContext)``.

    Args:
        intent:   Intent type string matching the client ``send({ type: "..." })``.
        in_state: Optional StateContext subclass — only active in that state.

    Example::

        @on_intent("shop.buy_minion", in_state=ShopStateContext)
        def handle_buy(self, player_id: str, payload: dict, ctx: ShopStateContext) -> None:
            slot = payload.get("slot")
            ...
    """
    def decorator(fn: Any) -> Any:
        fn._addon_intent = _IntentMeta(intent=intent, in_state=in_state)
        return fn
    return decorator


# ---------------------------------------------------------------------------
# EventResult
# ---------------------------------------------------------------------------

class EventResult(Enum):
    CONTINUE = auto()
    CANCEL = auto()

    @classmethod
    def cancel(cls) -> "EventResult":
        return cls.CANCEL

    @classmethod
    def continue_(cls) -> "EventResult":
        return cls.CONTINUE


# ---------------------------------------------------------------------------
# AddonBase
# ---------------------------------------------------------------------------

class AddonBase:
    """Base class for all server-side addons.

    Subclass and:
      - Set ``id`` (unique server-side identifier)
      - Declare ``cards: list[CardDef]`` if the addon contributes cards
      - Define ``MatchMemory(MatchScope)`` for match-wide typed memory
      - Define ``StateMemory(StateScope)`` for state-scoped typed memory
      - Use ``@on_event`` / ``@on_state`` / ``@on_intent`` decorators on methods
      - Override ``on_load(ctx)`` for one-time match-start setup
    """

    id: str = ""
    cards: list[CardDef] = []
    state_insertions: list[StateInsertion] = []

    class MatchMemory(MatchScope):
        """Override to declare match-wide typed memory fields."""

    class StateMemory(StateScope):
        """Override to declare state-scoped typed memory fields."""

    # Populated at install time by introspection
    _event_handlers: list[tuple[Callable[..., Any], _EventMeta]]
    _state_handlers: list[tuple[Callable[..., Any], _StateMeta]]
    _intent_handlers: list[tuple[Callable[..., Any], _IntentMeta]]

    def install(self, machine: StateMachine, catalog: Any) -> None:
        for card in self.cards:
            catalog.register(card)
        for insertion in self.state_insertions:
            machine.insert(insertion)
        machine.ctx.addons.append(self)

        self._event_handlers = []
        self._state_handlers = []
        self._intent_handlers = []
        for name in dir(self.__class__):
            method = getattr(self, name)
            if not callable(method):
                continue
            if hasattr(method, "_addon_event"):
                self._event_handlers.append((method, method._addon_event))
            if hasattr(method, "_addon_state"):
                self._state_handlers.append((method, method._addon_state))
            if hasattr(method, "_addon_intent"):
                self._intent_handlers.append((method, method._addon_intent))

        self.on_load(machine.ctx)

    def _dispatch_state(self, state_ctx: "StateContext", bus: EventBus) -> None:
        """Called by MatchContext.enter_state — wires event and state listeners."""
        for method, meta in self._state_handlers:
            if meta.ctx_type is None or isinstance(state_ctx, meta.ctx_type):
                method(state_ctx)

        for method, meta in self._event_handlers:
            if meta.in_state is None or isinstance(state_ctx, meta.in_state):
                _m = method
                _c = state_ctx

                def _handler(payload: Any, *, _method: Any = _m, _ctx: Any = _c) -> None:
                    _method(payload, _ctx)

                bus.on(meta.event, _handler, phase=meta.phase, priority=meta.priority)

    def _dispatch_intents(
        self, state_ctx: "StateContext", registry: dict[str, list[tuple[Any, _IntentMeta]]]
    ) -> None:
        """Called by MatchContext.enter_state — registers intent handlers for this state."""
        for method, meta in self._intent_handlers:
            if meta.in_state is None or isinstance(state_ctx, meta.in_state):
                handlers = registry.setdefault(meta.intent, [])
                handlers.append((method, meta))

    def on_load(self, ctx: "MatchContext") -> None:
        """Called once when the match is initialized. Override for one-time setup."""
