from ..base import CardDef
from ..base import DeathEvent
from ..base import Minion
from ...combat import CombatContext


def feast(minion: Minion, event: DeathEvent, ctx: CombatContext) -> None:
    if ctx.is_enemy(minion, event.subject, event.subject_side):
        ctx.buff(minion, attack=1, health=1)


CARD = CardDef(
    id="soul_collector",
    name="Soul Collector",
    base_attack=4,
    base_health=3,
    tier=3,
    description="Whenever an enemy dies in combat, gain +1/+1.",
    on_death=feast,
)
