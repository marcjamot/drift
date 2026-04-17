"""
Deterministic combat engine.

resolve_combat() takes deep copies of both boards and returns a full result
dict including every event in order — no mutation of live PlayerState occurs here.
"""

import random
from dataclasses import dataclass
from typing import Any, List, Optional

from ..cards.base import (
    AttackEvent,
    CardEvent,
    CombatStartEvent,
    DamageEvent,
    DeathEvent,
    Hook,
    KillEvent,
    Minion,
    SpawnEvent,
    TargetEvent,
    TriggerCtx,
)
from ..heroes.base import HeroDef
from ..player import BOARD_SIZE

CombatEvent = dict[str, Any]
CombatResult = dict[str, Any]


@dataclass
class CombatContext:
    friendly_board: List[Minion]
    enemy_board: List[Minion]
    events: List[CombatEvent]
    friendly_side: int = 0

    def deal_damage(self, minion: Minion, amount: int) -> int:
        actual = minion.take_damage(amount)
        self.events.append(
            {
                "type": "damage",
                "target_id": minion.instance_id,
                "target_name": minion.name,
                "amount": actual,
                "remaining_health": minion.health,
                "remaining_divine_shield": minion.divine_shield,
            }
        )
        return actual

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

    def summon(self, card_id: str, to_enemy: bool = False) -> Optional[Minion]:
        from ..cards.catalog import CARD_CATALOG

        board: List[Minion] = self.enemy_board if to_enemy else self.friendly_board
        if len(board) < BOARD_SIZE and card_id in CARD_CATALOG:
            m: Minion = CARD_CATALOG[card_id].create_instance()
            board.append(m)
            target_side: int = (1 - self.friendly_side) if to_enemy else self.friendly_side
            self.events.append(
                {
                    "type": "summon",
                    "card_id": card_id,
                    "minion": m.to_dict(),
                    "side": target_side,
                    "to_enemy": to_enemy,
                }
            )
            _dispatch_hooks(
                [self.friendly_board, self.enemy_board]
                if self.friendly_side == 0
                else [self.enemy_board, self.friendly_board],
                self.events,
                "on_spawn",
                SpawnEvent(subject=m, source="summon", subject_side=target_side),
                subject=m,
            )
            return m
        return None

    def add_keyword(self, minion: Minion, keyword: str) -> None:
        minion.keywords.add(keyword)
        self.events.append(
            {
                "type": "keyword_added",
                "target_id": minion.instance_id,
                "keyword": keyword,
            }
        )

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
        if subject is None:
            return False
        observer_side: int | None = self.side_of(observer)
        if observer_side is None:
            return False
        if subject_side is None:
            subject_side = self.side_of(subject)
        return subject_side == observer_side

    def is_enemy(
        self,
        observer: Minion,
        subject: Minion | None,
        subject_side: int | None = None,
    ) -> bool:
        if subject is None:
            return False
        observer_side: int | None = self.side_of(observer)
        if observer_side is None:
            return False
        if subject_side is None:
            subject_side = self.side_of(subject)
        return subject_side is not None and subject_side != observer_side

    def side_of(self, minion: Minion) -> int | None:
        if any(member.instance_id == minion.instance_id for member in self.friendly_board):
            return self.friendly_side
        if any(member.instance_id == minion.instance_id for member in self.enemy_board):
            return 1 - self.friendly_side
        return None


def _dispatch_hooks(
    boards: List[List[Minion]],
    events: List[CombatEvent],
    hook_name: str,
    event: CardEvent,
    subject: Optional[Minion] = None,
) -> None:
    """Dispatch a hook event through the 5-phase lifecycle.

    subject — the minion whose fn fires (e.g. the dying minion for on_death).
               If None, fn fires for every minion that has one (global events
               like on_combat_start where each card is its own subject).

    Phase order:
      1. start  — all cards; may call tctx.add_count / tctx.add_multiplier
      2. before — all cards; fires once per run (count * multiplier times)
      3. fn     — subject only (or all if subject is None); fires once per run
      4. after  — all cards; fires once per run
      5. end    — all cards; fires once after all runs
    """
    from ..cards.catalog import CARD_CATALOG

    entries: List[tuple] = []
    for side in range(2):
        for minion in list(boards[side]):
            card_def = CARD_CATALOG.get(minion.card_id)
            if not card_def:
                continue
            hook: Hook = getattr(card_def, hook_name)
            if hook.start or hook.before or hook.fn or hook.after or hook.end:
                entries.append((side, minion, hook))

    if not entries:
        return

    def _ctx(side: int) -> CombatContext:
        return CombatContext(
            friendly_board=boards[side],
            enemy_board=boards[1 - side],
            events=events,
            friendly_side=side,
        )

    # 1. start — all cards vote on count and multiplier.
    tctx = TriggerCtx()
    for side, minion, hook in entries:
        if hook.start:
            hook.start(minion, event, _ctx(side), tctx)

    # 2/3/4. before / fn / after — repeated count * multiplier times.
    for _ in range(tctx.total):
        for side, minion, hook in entries:
            if hook.before:
                hook.before(minion, event, _ctx(side))

        for side, minion, hook in entries:
            if not hook.fn:
                continue
            if subject is not None and minion.instance_id != subject.instance_id:
                continue
            hook.fn(minion, event, _ctx(side))

        for side, minion, hook in entries:
            if hook.after:
                hook.after(minion, event, _ctx(side))

    # 5. end — all cards, once after all runs.
    for side, minion, hook in entries:
        if hook.end:
            hook.end(minion, event, _ctx(side))


def _dispatch_hero_hooks(
    boards: List[List[Minion]],
    events: List[CombatEvent],
    hook_name: str,
    event: CardEvent,
    heroes: List[Optional[HeroDef]],
    subject_side: Optional[int] = None,
) -> None:
    """Fire a hero hook for the appropriate side(s).

    subject_side — if set, only fires the hero on that side (e.g. on_kill
                   fires for the killer's side; on_death for the dead
                   minion's side).  If None, fires both heroes (e.g.
                   on_combat_start affects every player).
    """
    for side, hero in enumerate(heroes):
        if hero is None:
            continue
        if subject_side is not None and side != subject_side:
            continue
        fn = getattr(hero, hook_name, None)
        if fn is None:
            continue
        ctx = CombatContext(
            friendly_board=boards[side],
            enemy_board=boards[1 - side],
            events=events,
            friendly_side=side,
        )
        fn(event, ctx)


def _choose_target(defending_board: List[Minion], rng: random.Random) -> Optional[Minion]:
    taunts: List[Minion] = [m for m in defending_board if m.is_alive() and "taunt" in m.keywords]
    if taunts:
        return rng.choice(taunts)
    alive: List[Minion] = [m for m in defending_board if m.is_alive()]
    return rng.choice(alive) if alive else None


def _next_attacker(board: List[Minion], start_idx: int) -> tuple[Optional[Minion], int]:
    if not board:
        return None, 0
    for offset in range(len(board)):
        idx = (start_idx + offset) % len(board)
        if board[idx].is_alive():
            return board[idx], idx
    return None, 0


def _advance_attacker_idx(board: List[Minion], previous_idx: int, attacker_id: str) -> int:
    if not board:
        return 0
    for idx, minion in enumerate(board):
        if minion.instance_id == attacker_id:
            return (idx + 1) % len(board)
    return previous_idx % len(board)


def _resolve_deaths(
    boards: List[List[Minion]],
    events: List[CombatEvent],
    heroes: List[Optional[HeroDef]],
    killer: Minion | None = None,
    killer_side: int | None = None,
) -> None:
    while True:
        resolved_any: bool = False

        for side in range(2):
            board: List[Minion] = boards[side]
            dead: List[Minion] = [m for m in list(board) if not m.is_alive()]

            for corpse in dead:
                if corpse not in board:
                    continue
                resolved_any = True
                events.append(
                    {
                        "type": "death",
                        "minion_id": corpse.instance_id,
                        "minion_name": corpse.name,
                        "player_idx": side,
                    }
                )
                death_event = DeathEvent(
                    subject=corpse,
                    subject_side=side,
                    actor=killer,
                    actor_side=killer_side,
                    killer=killer,
                    killer_side=killer_side,
                )
                _dispatch_hooks(boards, events, "on_death", death_event, subject=corpse)
                _dispatch_hero_hooks(boards, events, "on_death", death_event, heroes, subject_side=side)
                if corpse in board:
                    board.remove(corpse)

        if not resolved_any:
            break


def resolve_combat(
    board_a: List[Minion],
    board_b: List[Minion],
    rng: random.Random,
    tavern_tier_a: int,
    tavern_tier_b: int,
    hero_a: Optional[HeroDef] = None,
    hero_b: Optional[HeroDef] = None,
) -> CombatResult:
    boards: List[List[Minion]] = [
        [m.copy() for m in board_a],
        [m.copy() for m in board_b],
    ]
    events: List[CombatEvent] = []
    heroes: List[Optional[HeroDef]] = [hero_a, hero_b]

    combat_start = CombatStartEvent()
    _dispatch_hooks(boards, events, "on_combat_start", combat_start)
    _dispatch_hero_hooks(boards, events, "on_combat_start", combat_start, heroes)

    if len(boards[0]) > len(boards[1]):
        current: int = 0
    elif len(boards[1]) > len(boards[0]):
        current = 1
    else:
        current = rng.choice([0, 1])
    next_attacker_idx: List[int] = [0, 0]

    for _ in range(100):
        if not boards[0] or not boards[1]:
            break

        attacker, attacker_idx = _next_attacker(boards[current], next_attacker_idx[current])
        if attacker is None:
            current = 1 - current
            continue

        defender = _choose_target(boards[1 - current], rng)
        if defender is None:
            break

        target_event = TargetEvent(
            actor=attacker, actor_side=current,
            target=defender, target_side=1 - current,
        )
        _dispatch_hooks(boards, events, "on_target", target_event, subject=attacker)
        _dispatch_hero_hooks(boards, events, "on_target", target_event, heroes, subject_side=current)

        events.append(
            {
                "type": "attack",
                "attacker_id": attacker.instance_id,
                "attacker_name": attacker.name,
                "attacker_attack": attacker.attack,
                "defender_id": defender.instance_id,
                "defender_name": defender.name,
                "defender_attack": defender.attack,
            }
        )

        attack_event = AttackEvent(
            actor=attacker, actor_side=current,
            target=defender, target_side=1 - current,
        )
        _dispatch_hooks(boards, events, "on_attack", attack_event, subject=attacker)
        _dispatch_hero_hooks(boards, events, "on_attack", attack_event, heroes, subject_side=current)

        damage_to_attacker: int = attacker.take_damage(defender.attack)
        damage_to_defender: int = defender.take_damage(attacker.attack)

        dmg_attacker = DamageEvent(
            subject=attacker, subject_side=current,
            actor=defender, actor_side=1 - current,
            target=attacker, target_side=current,
            amount=damage_to_attacker,
        )
        _dispatch_hooks(boards, events, "on_damage", dmg_attacker, subject=attacker)
        _dispatch_hero_hooks(boards, events, "on_damage", dmg_attacker, heroes, subject_side=current)

        dmg_defender = DamageEvent(
            subject=defender, subject_side=1 - current,
            actor=attacker, actor_side=current,
            target=defender, target_side=1 - current,
            amount=damage_to_defender,
        )
        _dispatch_hooks(boards, events, "on_damage", dmg_defender, subject=defender)
        _dispatch_hero_hooks(boards, events, "on_damage", dmg_defender, heroes, subject_side=1 - current)

        if damage_to_defender > 0 and not defender.is_alive():
            kill_event = KillEvent(
                actor=attacker, actor_side=current,
                target=defender, target_side=1 - current,
                subject=attacker, subject_side=current,
            )
            _dispatch_hooks(boards, events, "on_kill", kill_event, subject=attacker)
            _dispatch_hero_hooks(boards, events, "on_kill", kill_event, heroes, subject_side=current)
        if damage_to_attacker > 0 and not attacker.is_alive():
            kill_event = KillEvent(
                actor=defender, actor_side=1 - current,
                target=attacker, target_side=current,
                subject=defender, subject_side=1 - current,
            )
            _dispatch_hooks(boards, events, "on_kill", kill_event, subject=defender)
            _dispatch_hero_hooks(boards, events, "on_kill", kill_event, heroes, subject_side=1 - current)

        events.append(
            {
                "type": "damage_dealt",
                "attacker_id": attacker.instance_id,
                "attacker_remaining_hp": attacker.health,
                "attacker_divine_shield": attacker.divine_shield,
                "damage_to_attacker": damage_to_attacker,
                "defender_id": defender.instance_id,
                "defender_remaining_hp": defender.health,
                "defender_divine_shield": defender.divine_shield,
                "damage_to_defender": damage_to_defender,
            }
        )

        _resolve_deaths(boards, events, heroes, killer=attacker, killer_side=current)
        next_attacker_idx[current] = _advance_attacker_idx(
            boards[current], attacker_idx, attacker.instance_id
        )
        current = 1 - current

    a_alive: List[Minion] = [m for m in boards[0] if m.is_alive()]
    b_alive: List[Minion] = [m for m in boards[1] if m.is_alive()]

    if a_alive and not b_alive:
        winner: Optional[int] = 0
        damage: int = tavern_tier_a + sum(m.tier for m in a_alive)
    elif b_alive and not a_alive:
        winner = 1
        damage = tavern_tier_b + sum(m.tier for m in b_alive)
    else:
        winner = None
        damage = 0

    return {
        "winner": winner,
        "damage": damage,
        "events": events,
        "surviving_a": [m.to_dict() for m in a_alive],
        "surviving_b": [m.to_dict() for m in b_alive],
    }
