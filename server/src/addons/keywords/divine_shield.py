from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from ...engine.actions import Action
from ...engine.addon import AddonBase, on_event
from ...engine.context import CombatStateContext
from ...engine.events import DamagePayload
from ...engine.memory import MatchScope, PerMinion


@dataclass
class DivineShieldBroken(Action):
    action_type: ClassVar[str] = "keyword.divine_shield_broken"
    target_id: str


class DivineShieldAddon(AddonBase):
    id = "keywords/divine_shield"

    class MatchMemory(MatchScope):
        divine_shield: PerMinion[bool] = False

    @on_event("damage", phase="pre", priority=100, in_state=CombatStateContext)
    def block_damage(self, payload: DamagePayload, ctx: CombatStateContext) -> None:
        if payload.amount <= 0:
            return
        mem = ctx.memory_match(self, payload.subject)
        if not mem.divine_shield:
            return
        mem.divine_shield = False
        ctx.emit(DivineShieldBroken(target_id=payload.subject.instance_id))
        payload.amount = 0
        payload.cancelled = True
