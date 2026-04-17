"""
CombatContext — the API card hooks receive during combat.

This is the primary interface for card authors. Every hook function that
fires during combat receives a CombatContext scoped to the hook's side
(friendly/enemy boards from that minion's perspective).
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, List, Optional

from ..cards.base import Minion, SpawnEvent
from ..player import BOARD_SIZE

CombatEvent = dict[str, Any]


def _combat_instance_id(boards: List[List[Minion]], events: List[CombatEvent], side: int) -> str:
    existing = {m.instance_id for board in boards for m in board}
    index = len(events)
    while True:
        candidate = f"c{side}{index:06x}"
        if candidate not in existing:
            return candidate
        index += 1


@dataclass
class CombatContext:
    friendly_board: List[Minion]
    enemy_board: List[Minion]
    events: List[CombatEvent]
    rng: random.Random = field(default_factory=random.Random)
    friendly_side: int = 0

    def deal_damage(self, minion: Minion, amount: int) -> int:
        actual = minion.take_damage(amount)
        self.events.append({
            "type": "damage",
            "target_id": minion.instance_id,
            "target_name": minion.name,
            "amount": actual,
            "remaining_health": minion.health,
            "remaining_divine_shield": minion.divine_shield,
        })
        return actual

    def buff(self, minion: Minion, attack: int = 0, health: int = 0) -> None:
        minion.attack = max(0, minion.attack + attack)
        minion.health += health
        minion.max_health += health
        self.events.append({
            "type": "buff",
            "target_id": minion.instance_id,
            "target_name": minion.name,
            "attack": attack,
            "health": health,
        })

    def summon(self, card_id: str, to_enemy: bool = False) -> Optional[Minion]:
        from ..cards.catalog import CARD_CATALOG
        from .engine import _dispatch_hooks  # deferred — avoids circular import

        board = self.enemy_board if to_enemy else self.friendly_board
        if len(board) >= BOARD_SIZE or card_id not in CARD_CATALOG:
            return None
        m = CARD_CATALOG[card_id].create_instance()
        boards = self._ordered_boards()
        board.append(m)
        target_side = (1 - self.friendly_side) if to_enemy else self.friendly_side
        m.instance_id = _combat_instance_id(boards, self.events, target_side)
        self.events.append({
            "type": "summon",
            "card_id": card_id,
            "minion": m.to_dict(),
            "side": target_side,
            "to_enemy": to_enemy,
        })
        _dispatch_hooks(
            boards, self.events, "on_spawn",
            SpawnEvent(subject=m, source="summon", subject_side=target_side),
            self.rng, subject=m,
        )
        return m

    def summon_copy(self, minion: Minion, to_enemy: bool = False) -> Optional[Minion]:
        from .engine import _dispatch_hooks

        board = self.enemy_board if to_enemy else self.friendly_board
        if len(board) >= BOARD_SIZE:
            return None
        m = minion.copy()
        boards = self._ordered_boards()
        board.append(m)
        target_side = (1 - self.friendly_side) if to_enemy else self.friendly_side
        m.instance_id = _combat_instance_id(boards, self.events, target_side)
        self.events.append({
            "type": "summon",
            "card_id": m.card_id,
            "minion": m.to_dict(),
            "side": target_side,
            "to_enemy": to_enemy,
        })
        _dispatch_hooks(
            boards, self.events, "on_spawn",
            SpawnEvent(subject=m, source="summon", subject_side=target_side),
            self.rng, subject=m,
        )
        return m

    def add_keyword(self, minion: Minion, keyword: str) -> None:
        minion.keywords.add(keyword)
        self.events.append({
            "type": "keyword_added",
            "target_id": minion.instance_id,
            "keyword": keyword,
        })

    def is_self(self, observer: Minion, subject: Optional[Minion]) -> bool:
        return subject is not None and observer.instance_id == subject.instance_id

    def is_other(self, observer: Minion, subject: Optional[Minion]) -> bool:
        return subject is not None and observer.instance_id != subject.instance_id

    def is_friendly(
        self,
        observer: Minion,
        subject: Optional[Minion],
        subject_side: Optional[int] = None,
    ) -> bool:
        if subject is None:
            return False
        observer_side = self.side_of(observer)
        if observer_side is None:
            return False
        if subject_side is None:
            subject_side = self.side_of(subject)
        return subject_side == observer_side

    def is_enemy(
        self,
        observer: Minion,
        subject: Optional[Minion],
        subject_side: Optional[int] = None,
    ) -> bool:
        if subject is None:
            return False
        observer_side = self.side_of(observer)
        if observer_side is None:
            return False
        if subject_side is None:
            subject_side = self.side_of(subject)
        return subject_side is not None and subject_side != observer_side

    def side_of(self, minion: Minion) -> Optional[int]:
        if any(m.instance_id == minion.instance_id for m in self.friendly_board):
            return self.friendly_side
        if any(m.instance_id == minion.instance_id for m in self.enemy_board):
            return 1 - self.friendly_side
        return None

    def _ordered_boards(self) -> List[List[Minion]]:
        if self.friendly_side == 0:
            return [self.friendly_board, self.enemy_board]
        return [self.enemy_board, self.friendly_board]
