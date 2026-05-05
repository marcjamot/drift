from .keywords import KEYWORD_ADDONS
from .neutrals import NeutralAddon

DEFAULT_ADDONS = [
    *KEYWORD_ADDONS,
    NeutralAddon,
]

__all__ = [
    "NeutralAddon",
    "DEFAULT_ADDONS",
]
