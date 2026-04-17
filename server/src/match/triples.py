"""
Triple detection and discover resolution.

Kept separate from actions.py so buy-phase mutations (check_triple is called
after every buy/play) are clearly isolated from the action dispatcher.
"""
from __future__ import annotations

import random
from collections import Counter
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..cards.base import Minion
    from ..cards.pool import CardPool
    from ..player.player import PlayerState


def check_triple(player: "PlayerState", pool: "CardPool", rng: random.Random) -> None:
    """Detect any card_id appearing 3+ times across hand+board and resolve it."""
    all_cards = [m.card_id for m in player.hand] + [m.card_id for m in player.board]
    counts = Counter(all_cards)
    for card_id, count in counts.items():
        if count >= 3:
            _resolve_triple(player, pool, rng, card_id)
            return


def _resolve_triple(
    player: "PlayerState",
    pool: "CardPool",
    rng: random.Random,
    card_id: str,
) -> None:
    from ..cards.catalog import CARD_CATALOG

    removed: List["Minion"] = []
    for collection in [player.hand, player.board]:
        i = 0
        while i < len(collection) and len(removed) < 3:
            if collection[i].card_id == card_id:
                removed.append(collection.pop(i))
            else:
                i += 1

    card_def = CARD_CATALOG[card_id]
    pool.return_cards(removed)
    golden = card_def.create_golden_instance()
    player.hand.append(golden)

    discover_tier = min(player.tavern_tier + 1, 6)
    options = pool.draw_at_tier(3, discover_tier)
    if len(options) < 3:
        options.extend(pool.draw(3 - len(options), discover_tier))
    player.pending_discover = options


def discover_pick(
    player: "PlayerState",
    index: Optional[int],
    pool: "CardPool",
    rng: random.Random,
) -> dict:
    if not player.pending_discover:
        return {"error": "no pending discover"}
    if index is None or not (0 <= index < len(player.pending_discover)):
        return {"error": "invalid discover index"}
    options = player.pending_discover
    chosen = options.pop(index)
    pool.return_cards(options)
    player.pending_discover = None
    player.hand.append(chosen)
    check_triple(player, pool, rng)
    return {"ok": True}


def auto_pick_discovers(player: "PlayerState", pool: "CardPool", rng: random.Random) -> None:
    while player.pending_discover:
        discover_pick(player, 0, pool, rng)
