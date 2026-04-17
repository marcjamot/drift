from ...base import CardDef
from ...base import Hook
from ...base import Minion
from ...base import SpawnEvent
from ...base import Tribe
from ....combat import CombatContext
from ....player import BuyContext


def shield_on_mech(minion: Minion, event: SpawnEvent, ctx: BuyContext | CombatContext) -> None:
    if not ctx.is_other(minion, event.subject):
        return
    if not ctx.is_friendly(minion, event.subject, event.subject_side):
        return
    if event.subject.tribe == Tribe.MECH:
        minion.divine_shield = True


CARD = CardDef(
    id="cobalt_guardian",
    name="Cobalt Guardian",
    base_attack=6,
    base_health=3,
    tier=3,
    description="Whenever you summon a Mech, gain Divine Shield.",
    on_spawn=Hook(after=shield_on_mech),
)
