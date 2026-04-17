"""Simple greedy bot AI for the buy phase."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..match.match import Match
    from ..player.player import PlayerState

from ..player.player import BOARD_SIZE, BUY_COST

logger = logging.getLogger(__name__)


def run_bot_buy_phase(player: "PlayerState", match: "Match") -> None:
    """Greedy bot: buy cards if affordable, play them all to board, then lock."""
    buy_phase = match._buy_phase

    # Try to buy one card from the shop (cheapest available)
    for i in range(len(player.shop)):
        if (
            player.gold >= BUY_COST
            and player.shop[i] is not None
            and len(player.hand) + len(player.board) < BOARD_SIZE + 2
        ):
            buy_phase._act_buy(player, {"type": "buy", "shop_index": i}, match)
            break  # buy at most one card per round to keep it simple

    # Play all cards in hand to board
    while player.hand and len(player.board) < BOARD_SIZE:
        buy_phase._act_play(player, {"type": "play", "hand_index": 0}, match)

    # Lock — set directly to avoid triggering the human-only phase-end check
    player.locked = True
