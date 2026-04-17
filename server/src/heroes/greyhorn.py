"""Greyhorn  —  passive (on_buy)

Passive: After buying a minion, give it +2/+0.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from .base import HeroDef

if TYPE_CHECKING:
    from ..cards.base import BuyEvent
    from ..player.player import BuyContext


def _on_buy(event: BuyEvent, ctx: BuyContext) -> None:
    ctx.buff(event.subject, attack=2, health=0)


HERO = HeroDef(
    id="greyhorn",
    name="Greyhorn",
    description="After buying a minion, give it +2/+0.",
    hero_power_type="passive",
    on_buy=_on_buy,
)
