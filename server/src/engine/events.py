from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from .models.card import Minion


@dataclass
class CombatStartPayload:
    event: str = "combat_start"


@dataclass
class TargetPayload:
    actor: "Minion"
    actor_side: int
    target: "Minion"
    target_side: int
    source_board: list["Minion"]
    target_board: list["Minion"]
    rng: Any = None
    event: str = "target"


@dataclass
class AttackPayload:
    actor: "Minion"
    actor_side: int
    target: "Minion"
    target_side: int
    source_board: list["Minion"]
    target_board: list["Minion"]
    deal_damage: Callable[..., int] | None = None
    repeat_actor: bool = False
    event: str = "attack"


@dataclass
class DamagePayload:
    source: "Minion"
    subject: "Minion"
    amount: int
    original_amount: int
    cancelled: bool = False
    event: str = "damage"


@dataclass
class DeathPayload:
    subject: "Minion"
    subject_side: int
    board: list["Minion"]
    position: int
    spawned: list["Minion"] = field(default_factory=list)
    event: str = "death"


@dataclass
class KillPayload:
    actor: "Minion"
    target: "Minion"
    actor_side: int
    target_side: int
    event: str = "kill"


@dataclass
class RoundStartPayload:
    player_id: str
    round: int
    event: str = "round_start"


EventPayload = (
    CombatStartPayload
    | TargetPayload
    | AttackPayload
    | DamagePayload
    | DeathPayload
    | KillPayload
    | RoundStartPayload
)
