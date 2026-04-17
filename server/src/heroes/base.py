from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

HeroDict = dict[str, Any]
HeroHook = Callable[[Any, Any], None]  # fn(event, ctx) -> None

# hero_power_type values:
#   "passive"             — fires automatically via event hooks, no button shown
#   "active_click"        — button in shop; fires once per round, no target
#   "active_target_shop"  — button enters targeting mode; player clicks a shop card
#   "active_target_hand"  — button enters targeting mode; player clicks a hand card


@dataclass(slots=True)
class HeroPowerEvent:
    """Passed to hero_power when the player activates an active power."""
    owner: Any = None           # PlayerState
    target: Any = None          # Minion (set for active_target_*)
    target_zone: str = ""       # "shop" | "hand"
    target_index: int = -1


@dataclass
class HeroDef:
    id: str
    name: str
    description: str

    # Power classification — determines UI and dispatch behaviour
    hero_power_type: str = "passive"   # see constants above
    hero_power: Optional[HeroHook] = field(default=None, repr=False)

    # Passive hooks (used only when hero_power_type == "passive")
    on_round_start:  Optional[HeroHook] = field(default=None, repr=False)
    on_buy:          Optional[HeroHook] = field(default=None, repr=False)
    on_sell:         Optional[HeroHook] = field(default=None, repr=False)
    on_play:         Optional[HeroHook] = field(default=None, repr=False)
    on_spawn:        Optional[HeroHook] = field(default=None, repr=False)
    on_combat_start: Optional[HeroHook] = field(default=None, repr=False)
    on_target:       Optional[HeroHook] = field(default=None, repr=False)
    on_attack:       Optional[HeroHook] = field(default=None, repr=False)
    on_damage:       Optional[HeroHook] = field(default=None, repr=False)
    on_kill:         Optional[HeroHook] = field(default=None, repr=False)
    on_death:        Optional[HeroHook] = field(default=None, repr=False)

    def to_dict(self) -> HeroDict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "power_type": self.hero_power_type,
        }
