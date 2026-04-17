"""Simple greedy bot AI for the buy phase."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..match.match import Match
    from ..player.player import PlayerState

from ..player.player import BOARD_SIZE, BUY_COST
from . import actions

logger = logging.getLogger(__name__)


def run_bot_buy_phase(player: "PlayerState", match: "Match") -> None:
    """Greedy bot: buy cards if affordable, play them all to board, then lock."""
    for i in range(len(player.shop)):
        if (
            player.gold >= BUY_COST
            and player.shop[i] is not None
            and len(player.hand) + len(player.board) < BOARD_SIZE + 2
        ):
            actions.buy(player, i, match.pool, match.rng)
            break

    while player.hand and len(player.board) < BOARD_SIZE:
        actions.play(player, 0, match.pool, match.rng)

    player.locked = True
