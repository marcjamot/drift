"""Sable, the Drifter  —  passive (on_combat_start)

Passive: At the start of combat, give all your minions +0/+1.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from .base import HeroDef

if TYPE_CHECKING:
    from ..cards.base import CombatStartEvent
    from ..combat.engine import CombatContext


def _on_combat_start(event: CombatStartEvent, ctx: CombatContext) -> None:
    for minion in list(ctx.friendly_board):
        ctx.buff(minion, attack=0, health=1)


HERO = HeroDef(
    id="sable",
    name="Sable, the Drifter",
    description="At the start of combat, give all your minions +0/+1.",
    armor=5,
    hero_power_type="passive",
    on_combat_start=_on_combat_start,
)
