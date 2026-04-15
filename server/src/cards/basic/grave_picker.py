from ..base import CardDef, Hook
from ..base import DeathEvent
from ..base import Minion
from ...combat import CombatContext


def harvest(minion: Minion, event: DeathEvent, ctx: CombatContext) -> None:
    if ctx.is_self(minion, event.subject):
        return
    if ctx.is_friendly(minion, event.subject, event.subject_side):
        ctx.buff(minion, health=1)


CARD = CardDef(
    id="grave_picker",
    name="Grave Picker",
    base_attack=3,
    base_health=2,
    tier=2,
    description="Whenever another friendly minion dies in combat, gain +1 Health.",
    on_death=Hook(after=harvest),
)
