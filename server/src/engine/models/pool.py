from __future__ import annotations

import random

from .card import CardDef, Minion

COPIES_PER_TIER = {1: 18, 2: 15, 3: 13, 4: 11, 5: 9, 6: 7}
SHOP_SIZE_BY_TIER = {1: 3, 2: 4, 3: 4, 4: 5, 5: 5, 6: 6}


class CardPool:
    def __init__(self, card_defs: list[CardDef], rng: random.Random) -> None:
        self.rng = rng
        self.defs = {card.id: card for card in card_defs}
        self.available: list[str] = []
        for card in card_defs:
            self.available.extend([card.id] * COPIES_PER_TIER.get(card.tier, 10))
        self.rng.shuffle(self.available)

    def draw(self, count: int, tier_limit: int) -> list[Minion]:
        eligible = [
            (index, card_id)
            for index, card_id in enumerate(self.available)
            if self.defs[card_id].tier <= tier_limit
        ]
        self.rng.shuffle(eligible)
        selected = eligible[:count]
        for index, _card_id in sorted(selected, key=lambda item: item[0], reverse=True):
            self.available.pop(index)
        return [self.defs[card_id].create_instance() for _index, card_id in selected]

    def draw_at_tier(self, count: int, tier: int) -> list[Minion]:
        eligible = [
            (index, card_id)
            for index, card_id in enumerate(self.available)
            if self.defs[card_id].tier == tier
        ]
        self.rng.shuffle(eligible)
        selected = eligible[:count]
        for index, _card_id in sorted(selected, key=lambda item: item[0], reverse=True):
            self.available.pop(index)
        return [self.defs[card_id].create_instance() for _index, card_id in selected]

    def return_card(self, card_def: CardDef) -> None:
        if card_def.id in self.defs:
            self.available.append(card_def.id)

    def return_minions(self, minions: list[Minion | None]) -> None:
        for minion in minions:
            if minion and minion.card_id in self.defs:
                self.available.append(minion.card_id)
