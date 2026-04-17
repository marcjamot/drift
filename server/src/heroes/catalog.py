from .base import HeroDef
from .greyhorn import HERO as GREYHORN
from .kron import HERO as KRON
from .mira import HERO as MIRA
from .sable import HERO as SABLE
from .zela import HERO as ZELA

HERO_CATALOG: dict[str, HeroDef] = {
    h.id: h for h in [MIRA, GREYHORN, SABLE, KRON, ZELA]
}

HERO_POOL: list[HeroDef] = list(HERO_CATALOG.values())
