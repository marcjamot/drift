from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Literal, TYPE_CHECKING

if TYPE_CHECKING:
    from .context import MatchContext

Condition = Callable[["MatchContext"], bool]


@dataclass
class Transition:
    condition: Condition
    next_state: str
    priority: int = 0


@dataclass
class StateInsertion:
    state: "State"
    position: Literal["before", "after"]
    anchor: str
    scope: Literal["first", "every"] = "first"
    transitions: list[Transition] = field(default_factory=list)


class State:
    name: str = "state"
    type: str = "state"
    deadline_seconds: float | None = None

    async def enter(self, ctx: "MatchContext") -> None:
        raise NotImplementedError

    async def exit(self, ctx: "MatchContext") -> None:
        return None

    def deadline(self, ctx: "MatchContext") -> float | None:
        if self.deadline_seconds is None:
            return None
        return time.monotonic() + self.deadline_seconds


class StateMachine:
    def __init__(self, ctx: "MatchContext", core_states: list[State]) -> None:
        self.ctx = ctx
        self.states: list[State] = list(core_states)
        self._by_name: dict[str, State] = {s.name: s for s in self.states}
        self.transition_table: dict[str, list[Transition]] = {}

    def add_transition(
        self,
        from_state: str,
        condition: Condition,
        to_state: str,
        *,
        priority: int = 0,
    ) -> None:
        bucket = self.transition_table.setdefault(from_state, [])
        bucket.append(Transition(condition=condition, next_state=to_state, priority=priority))
        bucket.sort(key=lambda t: t.priority, reverse=True)

    def remove_transitions_to(self, from_state: str, to_state: str) -> None:
        bucket = self.transition_table.get(from_state, [])
        self.transition_table[from_state] = [t for t in bucket if t.next_state != to_state]

    def insert(self, insertion: StateInsertion) -> None:
        indexes = [i for i, s in enumerate(self.states) if s.name == insertion.anchor]
        if insertion.scope == "first":
            indexes = indexes[:1]
        for offset, idx in enumerate(indexes):
            insert_at = idx + offset + (1 if insertion.position == "after" else 0)
            self.states.insert(insert_at, insertion.state)
        self._by_name = {s.name: s for s in self.states}
        for transition in insertion.transitions:
            self.add_transition(
                insertion.state.name,
                transition.condition,
                transition.next_state,
                priority=transition.priority,
            )

    def get(self, name: str) -> State:
        return self._by_name[name]

    async def run(self, start: str = "begin") -> None:
        current = self.get(start)
        while True:
            self.ctx.current_state = current
            self.ctx.current_deadline = current.deadline(self.ctx)
            self.ctx.replay.begin_state(self.ctx, current)
            await current.enter(self.ctx)
            await current.exit(self.ctx)
            self.ctx.replay.end_state()
            self.ctx.current_deadline = None
            self.ctx.event_bus.clear_temporary()
            transitions = self.transition_table.get(current.name, [])
            next_name: str | None = None
            for transition in transitions:
                if transition.condition(self.ctx):
                    next_name = transition.next_state
                    break
            if next_name is None:
                break
            current = self.get(next_name)
