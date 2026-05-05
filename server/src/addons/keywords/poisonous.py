from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from ...engine.actions import Action
from ...engine.addon import AddonBase, on_event
from ...engine.context import CombatStateContext
from ...engine.events import DamagePayload
from ...engine.memory import MatchScope, PerMinion


@dataclass
class PoisonousKill(Action):
    action_type: ClassVar[str] = "keyword.poisonous_kill"
    source_id: str
    target_id: str


class PoisonousAddon(AddonBase):
    id = "keywords/poisonous"

    class MatchMemory(MatchScope):
        poisonous: PerMinion[bool] = False

    @on_event("damage", phase="after", in_state=CombatStateContext)
    def poison_target(self, payload: DamagePayload, ctx: CombatStateContext) -> None:
        if payload.amount <= 0:
            return
        mem = ctx.memory_match(self, payload.source)
        if not mem.poisonous:
            return
        # Health of target is external state — passed as an explicit store delta
        ctx.emit(
            PoisonousKill(source_id=payload.source.instance_id, target_id=payload.subject.instance_id),
            store={f"minion:{payload.subject.instance_id}:health": 0},
        )
