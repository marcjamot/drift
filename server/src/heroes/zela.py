"""Zela, the Alchemist  —  active_target_hand

Power (once per round): Choose a minion in your hand. Give it +2/+2.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from .base import HeroDef, HeroPowerEvent

if TYPE_CHECKING:
    from ..player.player import BuyContext


def _hero_power(event: HeroPowerEvent, ctx: BuyContext) -> None:
    if event.target is not None:
        ctx.buff(event.target, attack=2, health=2)


HERO = HeroDef(
    id="zela",
    name="Zela, the Alchemist",
    description="Choose a minion in your hand. Give it +2/+2.",
    armor=10,
    hero_power_type="active_target_hand",
    hero_power=_hero_power,
)
