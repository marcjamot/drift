"""
Pure buy-phase action functions.

Each function takes explicit dependencies (player, pool, rng) rather than the
full Match object, making them trivially unit-testable without async infrastructure.
BuyPhase delegates all game-logic to these functions and handles only I/O concerns.
"""
from __future__ import annotations

import random
from typing import Any, Dict, Optional

from ..cards.base import BuyEvent, PlayEvent, SellEvent, SpawnEvent
from ..cards.pool import CardPool, SHOP_SIZE_BY_TIER
from ..player.player import (
    BOARD_SIZE,
    BUY_COST,
    BuyContext,
    PlayerState,
    REFRESH_COST,
    SELL_VALUE,
    compute_upgrade_cost,
)
from .triples import auto_pick_discovers as auto_pick_discovers
from .triples import check_triple
from .triples import discover_pick as discover_pick

ActionResult = Dict[str, Any]


# ── shop ──────────────────────────────────────────────────────────────────────

def refresh_shop(player: PlayerState, pool: CardPool) -> None:
    """Return current shop to pool and draw a fresh one. No gold cost."""
    pool.return_cards([m for m in player.shop if m is not None])
    size = SHOP_SIZE_BY_TIER.get(player.tavern_tier, 3)
    player.shop = pool.draw(size, player.tavern_tier)


# ── buy-phase actions ─────────────────────────────────────────────────────────

def buy(
    player: PlayerState,
    shop_index: Optional[int],
    pool: CardPool,
    rng: random.Random,
) -> ActionResult:
    if shop_index is None or not (0 <= shop_index < len(player.shop)):
        return {"error": "invalid shop_index"}
    minion = player.shop[shop_index]
    if minion is None:
        return {"error": "empty shop slot"}
    if player.gold < BUY_COST:
        return {"error": "not enough gold"}

    player.gold -= BUY_COST
    player.shop[shop_index] = None
    player.hand.append(minion)

    ctx = BuyContext(player=player, rng=rng)
    event = BuyEvent(subject=minion, owner=player, shop_index=shop_index)
    ctx.trigger("on_buy", event)
    ctx.trigger_hero("on_buy", event)
    check_triple(player, pool, rng)
    return {"ok": True}


def play(
    player: PlayerState,
    hand_index: Optional[int],
    pool: CardPool,
    rng: random.Random,
) -> ActionResult:
    if hand_index is None or not (0 <= hand_index < len(player.hand)):
        return {"error": "invalid hand_index"}
    if len(player.board) >= BOARD_SIZE:
        return {"error": "board is full"}

    minion = player.hand.pop(hand_index)
    player.board.append(minion)

    ctx = BuyContext(player=player, rng=rng)
    play_event = PlayEvent(subject=minion, owner=player, hand_index=hand_index, source="hand")
    spawn_event = SpawnEvent(subject=minion, source="play", owner=player)
    ctx.trigger("on_play", play_event)
    ctx.trigger_hero("on_play", play_event)
    ctx.trigger("on_spawn", spawn_event)
    ctx.trigger_hero("on_spawn", spawn_event)
    check_triple(player, pool, rng)
    return {"ok": True}


def sell(
    player: PlayerState,
    board_index: Optional[int],
    pool: CardPool,
    rng: random.Random,
) -> ActionResult:
    if board_index is None or not (0 <= board_index < len(player.board)):
        return {"error": "invalid board_index"}

    minion = player.board[board_index]
    ctx = BuyContext(player=player, rng=rng)
    sell_event = SellEvent(subject=minion, owner=player, board_index=board_index)
    ctx.trigger("on_sell", sell_event)
    ctx.trigger_hero("on_sell", sell_event)
    player.board.pop(board_index)
    player.gold = min(player.gold + SELL_VALUE, player.max_gold)
    pool.return_cards([minion])
    return {"ok": True}


def reorder(
    player: PlayerState,
    from_idx: Optional[int],
    to_idx: Optional[int],
) -> ActionResult:
    if from_idx is None or to_idx is None:
        return {"error": "from_index and to_index required"}
    if not (0 <= from_idx < len(player.board)):
        return {"error": "invalid from_index"}
    to_idx = max(0, min(to_idx, BOARD_SIZE - 1))
    minion = player.board.pop(from_idx)
    player.board.insert(min(to_idx, len(player.board)), minion)
    return {"ok": True}


def freeze(player: PlayerState) -> ActionResult:
    player.frozen = not player.frozen
    return {"ok": True}


def refresh(player: PlayerState, pool: CardPool) -> ActionResult:
    if player.gold < REFRESH_COST:
        return {"error": "not enough gold"}
    player.gold -= REFRESH_COST
    refresh_shop(player, pool)
    return {"ok": True}


def upgrade(player: PlayerState, round_num: int) -> ActionResult:
    if player.tavern_tier >= 6:
        return {"error": "already max tavern tier"}
    if player.gold < player.upgrade_cost:
        return {"error": "not enough gold"}
    player.gold -= player.upgrade_cost
    player.tavern_tier += 1
    player.upgrade_cost = compute_upgrade_cost(player.tavern_tier, round_num)
    return {"ok": True}


def lock(player: PlayerState) -> ActionResult:
    player.locked = True
    return {"ok": True}


def use_hero_power(
    player: PlayerState,
    action: Dict[str, Any],
    rng: random.Random,
) -> ActionResult:
    from ..heroes.base import HeroPowerEvent

    hero = player.hero
    if not hero or hero.hero_power_type == "passive" or not hero.hero_power:
        return {"error": "no active hero power"}
    if player.hero_power_uses_left <= 0:
        return {"error": "hero power already used this round"}

    target = None
    target_zone = ""
    target_index = -1

    if hero.hero_power_type.startswith("active_target_"):
        zone = action.get("target_zone")
        idx = action.get("target_index")
        if zone is None or idx is None:
            return {"error": "target_zone and target_index required"}
        expected = hero.hero_power_type.removeprefix("active_target_")
        if zone != expected:
            return {"error": f"must target a card in {expected}"}
        idx = int(idx)
        if zone == "shop":
            if not (0 <= idx < len(player.shop)) or player.shop[idx] is None:
                return {"error": "invalid shop target"}
            target = player.shop[idx]
        elif zone == "hand":
            if not (0 <= idx < len(player.hand)):
                return {"error": "invalid hand target"}
            target = player.hand[idx]
        target_zone = zone
        target_index = idx

    player.hero_power_uses_left -= 1
    ctx = BuyContext(player=player, rng=rng)
    hero.hero_power(
        HeroPowerEvent(
            owner=player,
            target=target,
            target_zone=target_zone,
            target_index=target_index,
        ),
        ctx,
    )
    return {"ok": True}


