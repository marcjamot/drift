from ...base import CardDef
from ...base import DeathEvent
from ...base import Hook
from ...base import Minion
from ...base import Tribe
from ....combat import CombatContext


def salvage(minion: Minion, event: DeathEvent, ctx: CombatContext) -> None:
    if not ctx.is_other(minion, event.subject):
        return
    if not ctx.is_friendly(minion, event.subject, event.subject_side):
        return
    if event.subject.tribe == Tribe.MECH:
        ctx.buff(minion, attack=2, health=2)


CARD = CardDef(
    id="junkbot",
    name="Junkbot",
    base_attack=1,
    base_health=5,
    tier=5,
    description="Whenever a friendly Mech dies, gain +2/+2.",
    on_death=Hook(after=salvage),
)
