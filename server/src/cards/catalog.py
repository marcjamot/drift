"""
Card catalog — all playable card definitions.

Each card is a CardDef with optional hook callables. Hooks receive:
  - minion: the Minion instance this card def belongs to
  - ctx:    BuyContext (buy/sell hooks) or CombatContext (combat hooks)

To add a new basic card: create a module in cards/basic and export `CARD`.
"""

from .base import CardDef
from .basic import BASIC_CARDS
from .tokens import TOKEN_CARDS

SHOP_CARDS: list[CardDef] = BASIC_CARDS
_CARDS: list[CardDef] = [*BASIC_CARDS, *TOKEN_CARDS]

CARD_CATALOG: dict[str, CardDef] = {c.id: c for c in _CARDS}
