from __future__ import annotations

from typing import ClassVar

from ..engine.context import StateContext
from ..engine.models import CardDef, Minion


class MinionCard(CardDef):
    card_id: ClassVar[str]
    card_name: ClassVar[str]
    attack: ClassVar[int]
    health: ClassVar[int]
    tavern_tier: ClassVar[int]
    text: ClassVar[str] = ""

    def __init__(self) -> None:
        super().__init__(
            id=self.card_id,
            name=self.card_name,
            base_attack=self.attack,
            base_health=self.health,
            tier=self.tavern_tier,
            description=self.text,
        )


class HeroCard(CardDef):
    card_id: ClassVar[str]
    card_name: ClassVar[str]
    text: ClassVar[str]
    armor_value: ClassVar[int] = 0
    power_type: ClassVar[str] = "passive"

    def __init__(self) -> None:
        super().__init__(
            id=self.card_id,
            name=self.card_name,
            base_attack=0,
            base_health=0,
            tier=0,
            cost=0,
            description=self.text,
            is_hero=True,
            armor=self.armor_value,
            hero_power_type=self.power_type,
        )

    def owner(self, hero: Minion, ctx: StateContext):
        owner_id = ctx.store.get(f"minion:{hero.instance_id}:owner_id")
        return ctx.match.players.get(owner_id) if owner_id else None


__all__ = ["HeroCard", "Minion", "MinionCard", "StateContext"]
