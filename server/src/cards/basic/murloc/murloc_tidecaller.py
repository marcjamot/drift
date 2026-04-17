from ...base import CardDef
from ...base import Hook
from ...base import Minion
from ...base import SpawnEvent
from ...base import Tribe
from ....combat import CombatContext
from ....player import BuyContext


def grow_on_murloc(minion: Minion, event: SpawnEvent, ctx: BuyContext | CombatContext) -> None:
    if not ctx.is_other(minion, event.subject):
        return
    if not ctx.is_friendly(minion, event.subject, event.subject_side):
        return
    if event.subject.tribe == Tribe.MURLOC:
        ctx.buff(minion, attack=1)


CARD = CardDef(
    id="murloc_tidecaller",
    name="Murloc Tidecaller",
    base_attack=1,
    base_health=2,
    tier=1,
    description="Whenever you summon a Murloc, gain +1 Attack.",
    on_spawn=Hook(after=grow_on_murloc),
)
