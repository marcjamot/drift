from ...engine.addon import AddonBase
from .cobalt_guard import CobaltGuard
from .ember import Ember
from .mirror_assassin import MirrorAssassin
from .phoenix_husk import PhoenixHusk
from .shield_bearer import ShieldBearer
from .sky_duelist import SkyDuelist
from .stone_golem import StoneGolem
from .storm_hydra import StormHydra


class NeutralAddon(AddonBase):
    id = "neutrals"

    def __init__(self) -> None:
        self.cards = [
            Ember(),
            StoneGolem(),
            ShieldBearer(),
            CobaltGuard(),
            SkyDuelist(),
            StormHydra(),
            PhoenixHusk(),
            MirrorAssassin(),
        ]
