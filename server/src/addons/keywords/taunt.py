from __future__ import annotations

from ...engine.addon import AddonBase, on_event
from ...engine.context import CombatStateContext
from ...engine.events import TargetPayload
from ...engine.memory import MatchScope, PerMinion
from ...engine.models import Minion


class TauntAddon(AddonBase):
    id = "keywords/taunt"

    class MatchMemory(MatchScope):
        taunt: PerMinion[bool] = False

    @on_event("target", phase="pre", priority=100, in_state=CombatStateContext)
    def force_taunt_target(self, payload: TargetPayload, ctx: CombatStateContext) -> None:
        board: list[Minion] = getattr(payload, "target_board", [])
        taunts = [m for m in board if m.is_alive() and ctx.memory_match(self, m).taunt]
        if not taunts:
            return
        rng = getattr(payload, "rng", None)
        payload.target = rng.choice(taunts) if rng else taunts[0]
