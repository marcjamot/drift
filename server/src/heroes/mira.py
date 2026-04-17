"""Mira, the Nurturer  —  active_click

Power (once per round): Give all friendly minions on your board +1/+1.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from .base import HeroDef, HeroPowerEvent

if TYPE_CHECKING:
    from ..player.player import BuyContext


def _hero_power(event: HeroPowerEvent, ctx: BuyContext) -> None:
    for minion in list(ctx.player.board):
        ctx.buff(minion, attack=1, health=1)


HERO = HeroDef(
    id="mira",
    name="Mira, the Nurturer",
    description="Give all friendly minions +1/+1.",
    hero_power_type="active_click",
    hero_power=_hero_power,
)
