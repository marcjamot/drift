"""Kron, the Warchief  —  active_target_shop

Power (once per round): Choose a minion in your shop. Give it +3/+0.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from .base import HeroDef, HeroPowerEvent

if TYPE_CHECKING:
    from ..player.player import BuyContext


def _hero_power(event: HeroPowerEvent, ctx: BuyContext) -> None:
    if event.target is not None:
        ctx.buff(event.target, attack=3, health=0)


HERO = HeroDef(
    id="kron",
    name="Kron, the Warchief",
    description="Choose a minion in your shop. Give it +3/+0.",
    armor=10,
    hero_power_type="active_target_shop",
    hero_power=_hero_power,
)
