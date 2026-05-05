from __future__ import annotations

from dataclasses import dataclass, field

from .card import CardDef


@dataclass
class CardCatalog:
    _cards: dict[str, CardDef] = field(default_factory=dict)

    def register(self, card_def: CardDef) -> None:
        self._cards[card_def.id] = card_def

    def get(self, card_id: str) -> CardDef:
        return self._cards[card_id]

    def maybe_get(self, card_id: str) -> CardDef | None:
        return self._cards.get(card_id)

    def all(self) -> list[CardDef]:
        return list(self._cards.values())

    def all_playable(self) -> list[CardDef]:
        return [card for card in self._cards.values() if not getattr(card, "is_hero", False)]

    def all_heroes(self) -> list[CardDef]:
        return [card for card in self._cards.values() if getattr(card, "is_hero", False)]
