from ...base import CardDef
from ...base import DamageEvent
from ...base import Minion
from ....combat import CombatContext


def frenzy(minion: Minion, event: DamageEvent, ctx: CombatContext) -> None:
    if not ctx.is_self(minion, event.subject):
        return
    if minion.is_alive() and event.amount > 0:
        ctx.buff(minion, attack=1)


CARD = CardDef(
    id="rustfang_hyena",
    name="Rustfang Hyena",
    base_attack=4,
    base_health=2,
    tier=2,
    description="Whenever this survives damage, gain +1 Attack.",
    on_damage=frenzy,
)
