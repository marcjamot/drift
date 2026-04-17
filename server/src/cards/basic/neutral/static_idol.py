from ...base import CardDef
from ...base import DamageEvent
from ...base import Minion
from ....combat import CombatContext


def zap_back(minion: Minion, event: DamageEvent, ctx: CombatContext) -> None:
    if ctx.is_self(minion, event.subject) and event.amount > 0:
        ctx.deal_damage(event.actor, 1)


CARD = CardDef(
    id="static_idol",
    name="Static Idol",
    base_attack=3,
    base_health=5,
    tier=3,
    description="Whenever this takes damage, deal 1 damage back to the attacker.",
    on_damage=zap_back,
)
