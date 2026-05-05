from __future__ import annotations

from ...engine.addon import AddonBase, on_event
from ...engine.context import CombatStateContext
from ...engine.events import AttackPayload
from ...engine.memory import MatchScope, PerMinion


class CleaveAddon(AddonBase):
    id = "keywords/cleave"

    class MatchMemory(MatchScope):
        cleave: PerMinion[bool] = False

    @on_event("attack", phase="after", in_state=CombatStateContext)
    def damage_adjacent(self, payload: AttackPayload, ctx: CombatStateContext) -> None:
        actor = payload.actor
        target = payload.target
        target_board = payload.target_board
        deal_damage = getattr(payload, "deal_damage", None)
        if deal_damage is None:
            return
        mem = ctx.memory_match(self, actor)
        if not mem.cleave:
            return
        if target not in target_board:
            return
        idx = target_board.index(target)
        for adj in (idx - 1, idx + 1):
            if 0 <= adj < len(target_board) and target_board[adj].is_alive():
                deal_damage(source=actor, subject=target_board[adj])
