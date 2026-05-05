from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..context import StateContext
    from ..store import Store


@dataclass
class Minion:
    card_id: str
    name: str
    tier: int
    description: str = ""
    instance_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    _local: dict[str, Any] = field(default_factory=dict, init=False, repr=False, compare=False)
    _store: "Store | None" = field(default=None, init=False, repr=False, compare=False)

    def _get(self, key: str, default: Any = None) -> Any:
        if self._store is not None:
            return self._store.get(f"minion:{self.instance_id}:{key}", default)
        return self._local.get(key, default)

    def _set(self, key: str, value: Any) -> None:
        if self._store is not None:
            self._store._set(f"minion:{self.instance_id}:{key}", value)
        else:
            self._local[key] = value

    @property
    def attack(self) -> int:
        return self._get("attack", 0)

    @attack.setter
    def attack(self, value: int) -> None:
        self._set("attack", value)

    @property
    def health(self) -> int:
        return self._get("health", 0)

    @health.setter
    def health(self, value: int) -> None:
        self._set("health", value)

    @property
    def golden(self) -> bool:
        return self._get("golden", False)

    @golden.setter
    def golden(self, value: bool) -> None:
        self._set("golden", value)

    def bind(self, store: "Store") -> "Minion":
        """Attach to match store, migrating any local state into it."""
        if self._store is not None:
            return self
        for key, value in self._local.items():
            store._set(f"minion:{self.instance_id}:{key}", value)
        self._store = store
        self._local.clear()
        return self

    def is_alive(self) -> bool:
        return self.health > 0

    def take_damage(self, amount: int) -> int:
        self.health -= amount
        return amount

    def copy(self) -> "Minion":
        """Create an unbound combat copy with a fresh instance_id."""
        new = Minion(
            card_id=self.card_id,
            name=self.name,
            tier=self.tier,
            description=self.description,
        )
        new._local = {
            "attack": self.attack,
            "health": self.health,
            "golden": self.golden,
        }
        return new

    def to_dict(self, extras: dict[str, Any] | None = None) -> dict[str, object]:
        return {
            "instance_id": self.instance_id,
            "card_id": self.card_id,
            "name": self.name,
            "description": self.description,
            "attack": self.attack,
            "health": self.health,
            "tier": self.tier,
            "golden": self.golden,
            "memory": extras or {},
        }


@dataclass
class CardDef:
    id: str
    name: str
    base_attack: int
    base_health: int
    tier: int
    cost: int = 3
    description: str = ""
    is_hero: bool = False
    armor: int = 0
    hero_power_type: str = "passive"

    def __post_init__(self) -> None:
        return None

    def on_load(self, minion: Minion) -> None:
        return None

    def on_state(self, minion: Minion, ctx: "StateContext") -> None:
        return None

    def create_instance(self) -> Minion:
        minion = Minion(
            card_id=self.id,
            name=self.name,
            description=self.description,
            tier=self.tier,
        )
        minion.attack = self.base_attack
        minion.health = self.base_health
        self.on_load(minion)
        return minion

    def create_golden_instance(self) -> Minion:
        minion = self.create_instance()
        minion.golden = True
        minion.attack = self.base_attack * 2
        minion.health = self.base_health * 2
        return minion

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "base_attack": self.base_attack,
            "base_health": self.base_health,
            "tier": self.tier,
            "cost": self.cost,
            "description": self.description,
            "is_hero": self.is_hero,
            "armor": self.armor,
            "power_type": self.hero_power_type if self.is_hero else None,
        }
