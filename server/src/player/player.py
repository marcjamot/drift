from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, List, Optional

from ..cards.base import CardEvent, Minion, SpawnEvent, TriggerCtx

if TYPE_CHECKING:
    from ..heroes.base import HeroDef

PlayerDict = dict[str, Any]
BuyEventData = dict[str, Any]

BOARD_SIZE = 7
MAX_GOLD = 10
REFRESH_COST = 1
BUY_COST = 3
SELL_VALUE = 1

# Base upgrade cost from tier N → N+1
UPGRADE_BASE_COSTS: dict[int, int] = {1: 5, 2: 7, 3: 8, 4: 9, 5: 10}


def gold_for_round(round_num: int) -> int:
    """Gold available at the start of round N (3, 4, 5, … capped at 10)."""
    return min(2 + round_num, MAX_GOLD)


def compute_upgrade_cost(current_tier: int, round_num: int) -> int:
    """
    Cost to upgrade from current_tier to current_tier+1, discounted by
    one gold per completed round (floor 0).
    """
    base = UPGRADE_BASE_COSTS.get(current_tier, 999)
    return max(0, base - (round_num - 1))


@dataclass
class BuyContext:
    player: "PlayerState"
    rng: random.Random
    events: List[BuyEventData] = field(default_factory=list)

    def buff(self, minion: Minion, attack: int = 0, health: int = 0) -> None:
        minion.attack = max(0, minion.attack + attack)
        minion.health += health
        minion.max_health += health
        self.events.append(
            {
                "type": "buff",
                "target_id": minion.instance_id,
                "target_name": minion.name,
                "attack": attack,
                "health": health,
            }
        )

    def summon_to_board(self, card_id: str) -> Optional[Minion]:
        from ..cards.catalog import CARD_CATALOG

        if len(self.player.board) < BOARD_SIZE and card_id in CARD_CATALOG:
            m: Minion = CARD_CATALOG[card_id].create_instance()
            self.player.board.append(m)
            self.events.append(
                {"type": "summon", "card_id": card_id, "minion": m.to_dict()}
            )
            self.trigger("on_spawn", SpawnEvent(subject=m, source="summon", owner=self.player))
            return m
        return None

    def trigger(self, hook_name: str, event: CardEvent) -> None:
        from ..cards.catalog import CARD_CATALOG

        for minion in list(self.player.board):
            card_def = CARD_CATALOG.get(minion.card_id)
            if not card_def:
                continue
            hook = getattr(card_def, hook_name, None)
            if not hook:
                continue
            tctx = TriggerCtx()
            if hook.start:
                hook.start(minion, event, self, tctx)
            for _ in range(tctx.total):
                if hook.before:
                    hook.before(minion, event, self)
                if hook.fn:
                    hook.fn(minion, event, self)
                if hook.after:
                    hook.after(minion, event, self)
            if hook.end:
                hook.end(minion, event, self)

    def trigger_hero(self, hook_name: str, event: CardEvent) -> None:
        hero = self.player.hero
        if hero is None:
            return
        fn = getattr(hero, hook_name, None)
        if fn:
            fn(event, self)

    def is_self(self, observer: Minion, subject: Minion | None) -> bool:
        return subject is not None and observer.instance_id == subject.instance_id

    def is_other(self, observer: Minion, subject: Minion | None) -> bool:
        return subject is not None and observer.instance_id != subject.instance_id

    def is_friendly(
        self,
        observer: Minion,
        subject: Minion | None,
        subject_side: int | None = None,
    ) -> bool:
        return subject is not None and any(
            member.instance_id == subject.instance_id for member in self.player.board
        )

    def is_enemy(self, observer: Minion, subject: Minion | None) -> bool:
        return False


@dataclass
class PlayerState:
    player_id: str
    name: str
    health: int = 40
    armor: int = 0
    gold: int = 0
    max_gold: int = 0
    tavern_tier: int = 1
    upgrade_cost: int = 5
    board: List[Minion] = field(default_factory=list)
    hand: List[Minion] = field(default_factory=list)
    shop: List[Optional[Minion]] = field(default_factory=list)  # None = bought slot
    frozen: bool = False
    locked: bool = False
    pending_discover: Optional[List[Minion]] = field(default=None)
    hero: Optional["HeroDef"] = field(default=None, repr=False)
    hero_power_uses_left: int = 0
    # Multiplayer / bot fields
    is_bot: bool = False
    last_combat_board: List[dict] = field(default_factory=list)
    mmr: int = 1000
    eliminated_round: Optional[int] = None
    placement: Optional[int] = None

    def __setattr__(self, name: str, value: Any) -> None:
        object.__setattr__(self, name, value)
        if name == "hero" and value is not None:
            object.__setattr__(self, "armor", value.armor)

    def start_round(self, round_num: int) -> None:
        self.max_gold = gold_for_round(round_num)
        self.gold = self.max_gold
        self.locked = False
        self.upgrade_cost = compute_upgrade_cost(self.tavern_tier, round_num)
        self.hero_power_uses_left = (
            1 if self.hero and self.hero.hero_power_type != "passive"
            else 0
        )

    def to_dict(self, as_self: bool = True) -> PlayerDict:
        base: PlayerDict = {
            "player_id": self.player_id,
            "name": self.name,
            "health": self.health,
            "armor": self.armor,
            "tavern_tier": self.tavern_tier,
            "locked": self.locked,
            "board": [m.to_dict() for m in self.board],
            "hero": self.hero.to_dict() if self.hero else None,
            "is_bot": self.is_bot,
        }
        if as_self:
            base.update(
                {
                    "hand": [m.to_dict() for m in self.hand],
                    "gold": self.gold,
                    "max_gold": self.max_gold,
                    "upgrade_cost": self.upgrade_cost,
                    "shop": [m.to_dict() if m else None for m in self.shop],
                    "frozen": self.frozen,
                    "hero_power_uses_left": self.hero_power_uses_left,
                }
            )
        return base
