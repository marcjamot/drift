from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from ...engine.actions import Action
from ...engine.addon import AddonBase, on_event
from ...engine.context import CombatStateContext
from ...engine.events import AttackPayload
from ...engine.memory import MatchScope, PerMinion


@dataclass
class WindfuryActivate(Action):
    action_type: ClassVar[str] = "keyword.windfury_activate"
    actor_id: str


class WindfuryAddon(AddonBase):
    id = "keywords/windfury"

    class MatchMemory(MatchScope):
        windfury: PerMinion[bool] = False
        windfury_used: PerMinion[bool] = False

    @on_event("attack", phase="after", in_state=CombatStateContext)
    def grant_second_attack(self, payload: AttackPayload, ctx: CombatStateContext) -> None:
        actor = payload.actor
        mem = ctx.memory_match(self, actor)
        if not mem.windfury or mem.windfury_used:
            return
        mem.windfury_used = True
        ctx.emit(WindfuryActivate(actor_id=actor.instance_id))
        payload.repeat_actor = True
