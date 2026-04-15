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
StartHook = Callable[["Minion", CardEvent, "TriggerCtx"], None]


@dataclass
class TriggerCtx:
    """Passed to Hook.start — controls how many times fn/before/after run.

    Final run count = count * multiplier.
    All start hooks on the board share this object and may modify both values.
    """

    count: int = 1
    multiplier: int = 1

    @property
    def total(self) -> int:
        return self.count * self.multiplier

    def add_count(self, extra: int = 1) -> None:
        self.count += extra

    def add_multiplier(self, extra: int = 1) -> None:
        self.multiplier += extra


@dataclass
class Hook:
    """
    Lifecycle wrapper for a single hook slot on a CardDef.

    Execution order per dispatch:
      1. start  — fires once before all runs; receives TriggerCtx to set count/multiplier
      2. before — fires before each individual run
      3. fn     — the main effect; fires N times (N determined by start hooks across all cards)
      4. after  — fires after each individual run
      5. end    — fires once after all runs

    Passing a plain callable where a Hook is expected is treated as Hook(fn=callable).
    """

    start:  Optional[StartHook] = None
    before: Optional[CardHook] = None
    fn:     Optional[CardHook] = None
    after:  Optional[CardHook] = None
    end:    Optional[CardHook] = None


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

    on_buy: Hook = field(default_factory=Hook)
    on_sell: Hook = field(default_factory=Hook)
    on_play: Hook = field(default_factory=Hook)
    on_spawn: Hook = field(default_factory=Hook)
    on_target: Hook = field(default_factory=Hook)
    on_attack: Hook = field(default_factory=Hook)
    on_damage: Hook = field(default_factory=Hook)
    on_kill: Hook = field(default_factory=Hook)
    on_death: Hook = field(default_factory=Hook)
    on_combat_start: Hook = field(default_factory=Hook)
    on_round_start: Hook = field(default_factory=Hook)

    _HOOK_FIELDS: tuple = field(init=False, repr=False, compare=False, default=(
        "on_buy", "on_sell", "on_play", "on_spawn", "on_target",
        "on_attack", "on_damage", "on_kill", "on_death",
        "on_combat_start", "on_round_start",
    ))

    def __post_init__(self) -> None:
        for name in self._HOOK_FIELDS:
            val = getattr(self, name)
            if callable(val) and not isinstance(val, Hook):
                setattr(self, name, Hook(fn=val))

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
