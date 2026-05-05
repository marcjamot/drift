from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import ClassVar

from ...engine.actions import Action
from ...engine.addon import AddonBase, on_event
from ...engine.context import CombatStateContext
from ...engine.events import DeathPayload
from ...engine.memory import MatchScope, PerMinion
from ...engine.models import BOARD_SIZE


@dataclass
class RebornTrigger(Action):
    action_type: ClassVar[str] = "keyword.reborn_trigger"
    source_id: str
    spawned_id: str


class RebornAddon(AddonBase):
    id = "keywords/reborn"

    class MatchMemory(MatchScope):
        reborn: PerMinion[bool] = False
        reborn_used: PerMinion[bool] = False

    @on_event("death", phase="after", in_state=CombatStateContext)
    def reborn_minion(self, payload: DeathPayload, ctx: CombatStateContext) -> None:
        subject = payload.subject
        board = payload.board
        position = payload.position

        mem = ctx.memory_match(self, subject)
        if not mem.reborn or mem.reborn_used or len(board) >= BOARD_SIZE:
            return

        reborn = subject.copy()
        reborn.instance_id = str(uuid.uuid4())[:8]
        reborn.health = 1

        reborn_mem = ctx.memory_match(self, reborn)
        mem.reborn_used = True
        reborn_mem.reborn = False
        ctx.emit(RebornTrigger(source_id=subject.instance_id, spawned_id=reborn.instance_id))

        board.insert(min(position, len(board)), reborn)
        payload.spawned.append(reborn)
