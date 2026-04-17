from types import ModuleType

from ..base import CardDef, TRIBES
from .beast import cub as cub_module
from .beast import phoenix as phoenix_module
from .neutral import ember as ember_module


def _card(module: ModuleType) -> CardDef:
    tribe = module.__name__.split(".")[-2]
    if tribe not in TRIBES:
        raise ValueError(f"Invalid card tribe folder: {tribe}")
    module.CARD.tribe = tribe
    return module.CARD


cub = _card(cub_module)
ember = _card(ember_module)
phoenix = _card(phoenix_module)

TOKEN_CARDS = [ember, cub, phoenix]
