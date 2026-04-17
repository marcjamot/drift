from ...base import CardDef
from ...base import Hook
from ...base import Minion
from ...base import SpawnEvent
from ...base import Tribe
from ....combat import CombatContext
from ....player import BuyContext


def reward_beast(minion: Minion, event: SpawnEvent, ctx: BuyContext | CombatContext) -> None:
    if not ctx.is_other(minion, event.subject):
        return
    if not ctx.is_friendly(minion, event.subject, event.subject_side):
        return
    if event.subject.tribe != Tribe.BEAST:
        return
    ctx.buff(event.subject, attack=2, health=2)


CARD = CardDef(
    id="mama_bear",
    name="Mama Bear",
    base_attack=4,
    base_health=4,
    tier=5,
    description="Whenever you summon a Beast, give it +2/+2.",
    on_spawn=Hook(after=reward_beast),
)
