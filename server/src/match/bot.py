from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..cards.base import Minion
    from ..match.match import Match
    from ..player.player import PlayerState

from ..cards.base import Tribe
from ..player.player import BOARD_SIZE, BUY_COST
from . import actions


def run_bot_buy_phase(player: "PlayerState", match: "Match") -> None:
    if player.gold < 1:
        actions.lock(player)
        return

    if player.tavern_tier < 4 and player.upgrade_cost <= player.gold * 0.4:
        actions.upgrade(player, match.round)

    _play_best_hand_cards(player, match)

    while player.gold >= BUY_COST and len(player.board) < BOARD_SIZE:
        shop_index = _best_shop_index(player)
        if shop_index is None:
            break

        result = actions.buy(player, shop_index, match.pool, match.rng)
        if "error" in result:
            break
        _play_best_hand_cards(player, match)

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


def _hand_score(card: "Minion", board: list["Minion"]) -> tuple[int, int, int]:
    tribe_count = _tribe_counts(board).get(card.tribe, 0)
    completes_tribe = card.tribe != Tribe.NEUTRAL and tribe_count + 1 >= 3
    matches_tribe = card.tribe != Tribe.NEUTRAL and tribe_count > 0
    return (
        2 if completes_tribe else 1 if matches_tribe else 0,
        card.attack + card.health,
        -card.tier,
    )


def _best_shop_index(player: "PlayerState") -> int | None:
    candidates = [
        (i, card)
        for i, card in enumerate(player.shop)
        if card is not None
    ]
    if not candidates:
        return None

    board_tribes = _tribe_counts(player.board)
    return max(
        candidates,
        key=lambda item: _shop_score(item[1], board_tribes),
    )[0]


def _shop_score(card: "Minion", board_tribes: Counter[str]) -> tuple[int, int, int]:
    matches_tribe = (
        card.tribe != Tribe.NEUTRAL
        and board_tribes.get(card.tribe, 0) > 0
    )
    return (
        1 if matches_tribe else 0,
        card.attack + card.health,
        -card.tier,
    )


def _should_freeze_for_shop(player: "PlayerState") -> bool:
    board_tribes = _tribe_counts(player.board)
    return any(
        card is not None
        and (
            card.attack + card.health >= 6
            or (card.tribe != Tribe.NEUTRAL and board_tribes.get(card.tribe, 0) > 0)
        )
        for card in player.shop
    )


def _tribe_counts(cards: list["Minion"]) -> Counter[str]:
    return Counter(card.tribe for card in cards if card.tribe != Tribe.NEUTRAL)
