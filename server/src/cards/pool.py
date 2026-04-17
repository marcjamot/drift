import random
from typing import Dict, List

from .base import CardDef, Minion

# Copies of each card available in the shared pool, per tier
COPIES_PER_TIER: Dict[int, int] = {1: 18, 2: 15, 3: 13, 4: 11, 5: 9, 6: 7}

# Number of minions shown in shop at each tavern tier
SHOP_SIZE_BY_TIER: Dict[int, int] = {1: 3, 2: 4, 3: 4, 4: 5, 5: 5, 6: 6}


class CardPool:
    """
    Shared pool of card instances. Both players draw from and return to this pool.
    Drawing is deterministic via the seeded rng passed at construction.
    """

    def __init__(self, card_defs: List[CardDef], rng: random.Random) -> None:
        self.rng = rng
        self.defs: Dict[str, CardDef] = {c.id: c for c in card_defs}

        # Flat list of card_ids representing all available copies
        self.available: List[str] = []
        for card in card_defs:
            copies = COPIES_PER_TIER.get(card.tier, 10)
            self.available.extend([card.id] * copies)
        self.rng.shuffle(self.available)

    def draw(self, count: int, tier_limit: int) -> List[Minion]:
        """
        Draw up to `count` minions whose tier <= tier_limit.
        Drawn cards are removed from the pool.
        """
        eligible: List[tuple[int, str]] = [
            (i, cid)
            for i, cid in enumerate(self.available)
            if self.defs[cid].tier <= tier_limit
        ]
        self.rng.shuffle(eligible)
        selected: List[tuple[int, str]] = eligible[:count]

        # Remove selected indices in descending order to preserve positions
        for idx, _ in sorted(selected, key=lambda x: x[0], reverse=True):
            self.available.pop(idx)

        return [self.defs[cid].create_instance() for _, cid in selected]

    def draw_at_tier(self, count: int, tier: int) -> List[Minion]:
        """Draw up to count minions of exactly the given tier."""
        eligible: List[tuple[int, str]] = [
            (i, cid)
            for i, cid in enumerate(self.available)
            if self.defs[cid].tier == tier
        ]
        self.rng.shuffle(eligible)
        selected: List[tuple[int, str]] = eligible[:count]
        for idx, _ in sorted(selected, key=lambda x: x[0], reverse=True):
            self.available.pop(idx)
        return [self.defs[cid].create_instance() for _, cid in selected]

    def return_cards(self, minions: List[Minion | None]) -> None:
        """Return minions back to the available pool."""
        for m in minions:
            if m is not None and m.card_id in self.defs:
                self.available.append(m.card_id)

    def get_def(self, card_id: str) -> CardDef | None:
        return self.defs.get(card_id)
