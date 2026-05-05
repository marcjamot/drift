from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .card import CardDef, Minion

if TYPE_CHECKING:
    from ..store import Store

BOARD_SIZE = 7
MAX_GOLD = 10
REFRESH_COST = 1
BUY_COST = 3
SELL_VALUE = 1
UPGRADE_BASE_COSTS = {1: 5, 2: 7, 3: 8, 4: 9, 5: 10}


def gold_for_round(round_num: int) -> int:
    return min(2 + round_num, MAX_GOLD)


def compute_upgrade_cost(current_tier: int, round_num: int) -> int:
    return max(0, UPGRADE_BASE_COSTS.get(current_tier, 999) - (round_num - 1))


_PLAYER_DEFAULTS: dict[str, Any] = {
    "health": 40,
    "armor": 0,
    "gold": 0,
    "max_gold": 0,
    "tavern_tier": 1,
    "upgrade_cost": 5,
    "frozen": False,
    "locked": False,
    "ghost": False,
    "mmr": 1000,
    "placement": None,
    "eliminated_round": None,
    "hero_power_uses_left": 0,
}


@dataclass
class PlayerState:
    # Static identity (never in store)
    player_id: str
    name: str
    is_bot: bool = False
    # Object-typed state
    board: list[Minion] = field(default_factory=list)
    hand: list[Minion] = field(default_factory=list)
    shop: list[Minion | None] = field(default_factory=list)
    pending_discover: list[Minion] | None = None
    hero: CardDef | None = None
    hero_subject: Minion | None = field(default=None, repr=False)
    last_combat_board: list[dict[str, Any]] = field(default_factory=list)
    # Store infrastructure
    _local: dict[str, Any] = field(
        default_factory=lambda: dict(_PLAYER_DEFAULTS),
        init=False, repr=False, compare=False,
    )
    _store: "Store | None" = field(default=None, init=False, repr=False, compare=False)

    def _get(self, key: str, default: Any = None) -> Any:
        if self._store is not None:
            return self._store.get(f"player:{self.player_id}:{key}", default)
        return self._local.get(key, default)

    def _set(self, key: str, value: Any) -> None:
        if self._store is not None:
            self._store._set(f"player:{self.player_id}:{key}", value)
        else:
            self._local[key] = value

    def bind(self, store: "Store") -> "PlayerState":
        """Attach to match store, migrating all local scalar state into it."""
        if self._store is not None:
            return self
        for key, value in self._local.items():
            store._set(f"player:{self.player_id}:{key}", value)
        self._store = store
        return self

    # --- scalar state as store-backed properties ---

    @property
    def health(self) -> int:
        return self._get("health", 40)

    @health.setter
    def health(self, value: int) -> None:
        self._set("health", value)

    @property
    def armor(self) -> int:
        return self._get("armor", 0)

    @armor.setter
    def armor(self, value: int) -> None:
        self._set("armor", value)

    @property
    def gold(self) -> int:
        return self._get("gold", 0)

    @gold.setter
    def gold(self, value: int) -> None:
        self._set("gold", value)

    @property
    def max_gold(self) -> int:
        return self._get("max_gold", 0)

    @max_gold.setter
    def max_gold(self, value: int) -> None:
        self._set("max_gold", value)

    @property
    def tavern_tier(self) -> int:
        return self._get("tavern_tier", 1)

    @tavern_tier.setter
    def tavern_tier(self, value: int) -> None:
        self._set("tavern_tier", value)

    @property
    def upgrade_cost(self) -> int:
        return self._get("upgrade_cost", 5)

    @upgrade_cost.setter
    def upgrade_cost(self, value: int) -> None:
        self._set("upgrade_cost", value)

    @property
    def frozen(self) -> bool:
        return self._get("frozen", False)

    @frozen.setter
    def frozen(self, value: bool) -> None:
        self._set("frozen", value)

    @property
    def locked(self) -> bool:
        return self._get("locked", False)

    @locked.setter
    def locked(self, value: bool) -> None:
        self._set("locked", value)

    @property
    def ghost(self) -> bool:
        return self._get("ghost", False)

    @ghost.setter
    def ghost(self, value: bool) -> None:
        self._set("ghost", value)

    @property
    def mmr(self) -> int:
        return self._get("mmr", 1000)

    @mmr.setter
    def mmr(self, value: int) -> None:
        self._set("mmr", value)

    @property
    def placement(self) -> int | None:
        return self._get("placement", None)

    @placement.setter
    def placement(self, value: int | None) -> None:
        self._set("placement", value)

    @property
    def eliminated_round(self) -> int | None:
        return self._get("eliminated_round", None)

    @eliminated_round.setter
    def eliminated_round(self, value: int | None) -> None:
        self._set("eliminated_round", value)

    @property
    def hero_power_uses_left(self) -> int:
        return self._get("hero_power_uses_left", 0)

    @hero_power_uses_left.setter
    def hero_power_uses_left(self, value: int) -> None:
        self._set("hero_power_uses_left", value)

    # --- game logic ---

    def start_round(self, round_num: int) -> None:
        self.max_gold = gold_for_round(round_num)
        self.gold = self.max_gold
        self.locked = False
        self.upgrade_cost = compute_upgrade_cost(self.tavern_tier, round_num)
        self.hero_power_uses_left = 0 if not self.hero or self.hero.hero_power_type == "passive" else 1

    def set_hero(self, hero: CardDef) -> None:
        self.hero = hero
        self.armor = hero.armor

    def to_dict(self, as_self: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "player_id": self.player_id,
            "name": self.name,
            "health": self.health,
            "armor": self.armor,
            "tavern_tier": self.tavern_tier,
            "locked": self.locked,
            "board": self.last_combat_board if self.ghost else [m.to_dict() for m in self.board],
            "hero": self.hero.to_dict() if self.hero else None,
            "is_bot": self.is_bot,
            "is_ghost": self.ghost,
            "placement": self.placement,
        }
        if as_self:
            payload.update({
                "hand": [m.to_dict() for m in self.hand],
                "gold": self.gold,
                "max_gold": self.max_gold,
                "upgrade_cost": self.upgrade_cost,
                "shop": [m.to_dict() if m else None for m in self.shop],
                "frozen": self.frozen,
                "hero_power_uses_left": self.hero_power_uses_left,
            })
        return payload
