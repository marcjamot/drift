from __future__ import annotations

from ..engine.context import MatchContext, StateContext
from ..engine.state_machine import State


class BeginState(State):
    name = "begin"
    type = "begin"

    async def enter(self, ctx: MatchContext) -> None:
        ctx.phase = self.type
        ctx.enter_state(StateContext(type=self.type, match=ctx))
        ctx.replay.update_current_snapshot(ctx)
        ctx.event_bus.emit({"event": "state_enter", "state": self.name, "ctx": ctx.state_context})
