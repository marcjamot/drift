from ...base import CardDef, Hook
from ...base import DeathEvent
from ...base import Minion
from ....combat import CombatContext


def grow_on_death(minion: Minion, event: DeathEvent, ctx: CombatContext) -> None:
    if ctx.is_self(minion, event.subject):
        return
    if not ctx.is_friendly(minion, event.subject, event.subject_side):
        return
    ctx.buff(minion, attack=1, health=1)

CARD = CardDef(
    id="iron_automaton",
    name="Iron Automaton",
    base_attack=1,
    base_health=3,
    tier=2,
    description="Whenever a friendly minion dies in combat, gain +1/+1.",
    on_death=Hook(after=grow_on_death),
)
