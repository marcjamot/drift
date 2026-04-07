from __future__ import annotations

import copy
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Set

CardDict = dict[str, Any]
CardContext = Any


@dataclass(slots=True)
class CardEvent:
    pass


@dataclass(slots=True)
class BuyEvent(CardEvent):
    subject: "Minion"
    owner: Any
    shop_index: int
    source: str = "shop"


@dataclass(slots=True)
class SellEvent(CardEvent):
    subject: "Minion"
    owner: Any
    board_index: int


@dataclass(slots=True)
class PlayEvent(CardEvent):
    subject: "Minion"
    owner: Any
    shop_index: int | None = None
    hand_index: int | None = None
    source: str = "hand"


@dataclass(slots=True)
class SpawnEvent(CardEvent):
    subject: "Minion"
    source: str
    owner: Any | None = None
    subject_side: int | None = None


@dataclass(slots=True)
class TargetEvent(CardEvent):
    actor: "Minion"
    actor_side: int
    target: "Minion"
    target_side: int


@dataclass(slots=True)
class AttackEvent(CardEvent):
    actor: "Minion"
    actor_side: int
    target: "Minion"
    target_side: int


@dataclass(slots=True)
class DamageEvent(CardEvent):
    subject: "Minion"
    subject_side: int
    actor: "Minion"
    actor_side: int
    target: "Minion"
    target_side: int
    amount: int


@dataclass(slots=True)
class KillEvent(CardEvent):
    actor: "Minion"
    actor_side: int
    target: "Minion"
    target_side: int
    subject: "Minion"
    subject_side: int


@dataclass(slots=True)
class DeathEvent(CardEvent):
    subject: "Minion"
    subject_side: int
    actor: "Minion" | None = None
    actor_side: int | None = None
    killer: "Minion" | None = None
    killer_side: int | None = None


@dataclass(slots=True)
class CombatStartEvent(CardEvent):
    pass


@dataclass(slots=True)
class RoundStartEvent(CardEvent):
    round: int
    owner: Any


CardHook = Callable[["Minion", CardEvent, Any], None]


@dataclass
class Minion:
    """Runtime instance of a minion placed on a board."""

    card_id: str
    name: str
    description: str
    attack: int
    health: int
    max_health: int
    tier: int
    instance_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    keywords: Set[str] = field(default_factory=set)
    divine_shield: bool = False
    golden: bool = False

    def is_alive(self) -> bool:
        return self.health > 0

    def take_damage(self, amount: int) -> int:
        """Returns actual damage dealt (0 if absorbed by divine shield)."""
        if self.divine_shield:
            self.divine_shield = False
            return 0
        self.health -= amount
        return amount

    def to_dict(self) -> CardDict:
        return {
            "instance_id": self.instance_id,
            "card_id": self.card_id,
            "name": self.name,
            "description": self.description,
            "attack": self.attack,
            "health": self.health,
            "max_health": self.max_health,
            "tier": self.tier,
            "keywords": list(self.keywords),
            "divine_shield": self.divine_shield,
            "golden": self.golden,
        }

    def copy(self) -> "Minion":
        return copy.deepcopy(self)


@dataclass
class CardDef:
    id: str
    name: str
    base_attack: int
    base_health: int
    tier: int
    cost: int = 3
    keywords: list[str] = field(default_factory=list)
    description: str = ""

    on_buy: Optional[CardHook] = None
    on_sell: Optional[CardHook] = None
    on_play: Optional[CardHook] = None
    on_spawn: Optional[CardHook] = None
    on_target: Optional[CardHook] = None
    on_attack: Optional[CardHook] = None
    on_damage: Optional[CardHook] = None
    on_kill: Optional[CardHook] = None
    on_death: Optional[CardHook] = None
    on_combat_start: Optional[CardHook] = None
    on_round_start: Optional[CardHook] = None

    def create_instance(self) -> Minion:
        return Minion(
            card_id=self.id,
            name=self.name,
            description=self.description,
            attack=self.base_attack,
            health=self.base_health,
            max_health=self.base_health,
            tier=self.tier,
            keywords=set(self.keywords),
            divine_shield="divine_shield" in self.keywords,
        )

    def to_dict(self) -> CardDict:
        return {
            "id": self.id,
            "name": self.name,
            "base_attack": self.base_attack,
            "base_health": self.base_health,
            "tier": self.tier,
            "cost": self.cost,
            "keywords": self.keywords,
            "description": self.description,
        }
