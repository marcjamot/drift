from ...base import CardDef
from ...base import DamageEvent
from ...base import Minion
from ....combat import CombatContext


def summon_imp(minion: Minion, event: DamageEvent, ctx: CombatContext) -> None:
    if not ctx.is_self(minion, event.subject):
        return
    if event.amount <= 0:
        return
    ctx.summon("imp", after=minion)


CARD = CardDef(
    id="imp_gang_boss",
    name="Imp Gang Boss",
    base_attack=2,
    base_health=4,
    tier=3,
    description="Whenever this takes damage, summon a 1/1 Imp.",
    on_damage=summon_imp,
)
