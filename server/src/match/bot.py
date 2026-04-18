from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from ..cards.base import Minion
    from ..match.match import Match
    from ..player.player import PlayerState

from ..cards.base import Tribe
from ..player.player import BOARD_SIZE, BUY_COST
from . import actions
from .triples import auto_pick_discovers


class CardScore(NamedTuple):
    """Comparable score for ranking cards. Higher is better (compared tuple-wise)."""
    tribe_bonus: int   # 2=completes a tribe run, 1=matches existing tribe, 0=no match
    stats: int         # attack + health
    tier_neg: int      # negative tier — prefer lower-tier cards early in the game


def run_bot_buy_phase(player: "PlayerState", match: "Match") -> None:
    if player.gold < 1:
        auto_pick_discovers(player, match.pool, match.rng)
        actions.lock(player)
        return

    if player.tavern_tier < 4 and player.upgrade_cost <= player.gold * 0.4:
        actions.upgrade(player, match.round)
        auto_pick_discovers(player, match.pool, match.rng)

    _play_best_hand_cards(player, match)
    auto_pick_discovers(player, match.pool, match.rng)

    while player.gold >= BUY_COST and len(player.board) < BOARD_SIZE:
        shop_index = _best_shop_index(player)
        if shop_index is None:
            break
        result = actions.buy(player, shop_index, match.pool, match.rng)
        if "error" in result:
            break
        auto_pick_discovers(player, match.pool, match.rng)
        _play_best_hand_cards(player, match)
        auto_pick_discovers(player, match.pool, match.rng)

    if player.gold == 1 and _should_freeze_for_shop(player) and not player.frozen:
        actions.freeze(player)

    actions.lock(player)


def _play_best_hand_cards(player: "PlayerState", match: "Match") -> None:
    while player.hand and len(player.board) < BOARD_SIZE:
        hand_index = max(
            range(len(player.hand)),
            key=lambda i: _hand_score(player.hand[i], player.board),
        )
        result = actions.play(player, hand_index, match.pool, match.rng)
        if "error" in result:
            break


def _hand_score(card: "Minion", board: list["Minion"]) -> CardScore:
    tribe_count = _tribe_counts(board).get(card.tribe, 0)
    completes_tribe = card.tribe != Tribe.NEUTRAL and tribe_count + 1 >= 3
    matches_tribe = card.tribe != Tribe.NEUTRAL and tribe_count > 0
    return CardScore(
        tribe_bonus=2 if completes_tribe else 1 if matches_tribe else 0,
        stats=card.attack + card.health,
        tier_neg=-card.tier,
    )


def _best_shop_index(player: "PlayerState") -> int | None:
    candidates = [(i, c) for i, c in enumerate(player.shop) if c is not None]
    if not candidates:
        return None
    board_tribes = _tribe_counts(player.board)
    return max(candidates, key=lambda item: _shop_score(item[1], board_tribes))[0]


def _shop_score(card: "Minion", board_tribes: Counter[str]) -> CardScore:
    matches_tribe = card.tribe != Tribe.NEUTRAL and board_tribes.get(card.tribe, 0) > 0
    return CardScore(
        tribe_bonus=1 if matches_tribe else 0,
        stats=card.attack + card.health,
        tier_neg=-card.tier,
    )


def _should_freeze_for_shop(player: "PlayerState") -> bool:
    board_tribes = _tribe_counts(player.board)
    return any(
        c is not None and (
            c.attack + c.health >= 6
            or (c.tribe != Tribe.NEUTRAL and board_tribes.get(c.tribe, 0) > 0)
        )
        for c in player.shop
    )


def _tribe_counts(cards: list["Minion"]) -> Counter[str]:
    return Counter(c.tribe for c in cards if c.tribe != Tribe.NEUTRAL)
