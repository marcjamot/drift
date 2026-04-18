from types import ModuleType

from ..base import CardDef, TRIBES
from .beast import cub as cub_module
from .beast import phoenix as phoenix_module
from .neutral import ember as ember_module
from .neutral import imp as imp_module
from .pirate import sky_pirate as sky_pirate_module


def _card(module: ModuleType) -> CardDef:
    tribe = module.__name__.split(".")[-2]
    if tribe not in TRIBES:
        raise ValueError(f"Invalid card tribe folder: {tribe}")
    module.CARD.tribe = tribe
    return module.CARD


cub = _card(cub_module)
ember = _card(ember_module)
imp = _card(imp_module)
phoenix = _card(phoenix_module)
sky_pirate = _card(sky_pirate_module)

TOKEN_CARDS = [ember, imp, cub, phoenix, sky_pirate]
