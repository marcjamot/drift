from ...base import CardDef
from ...base import DeathEvent
from ...base import Minion
from ....combat import CombatContext


def deathrattle(minion: Minion, event: DeathEvent, ctx: CombatContext) -> None:
    if ctx.is_self(minion, event.subject):
        ctx.summon("ember", after=minion)


CARD = CardDef(
    id="ashen_rat",
    name="Ashen Rat",
    base_attack=2,
    base_health=1,
    tier=1,
    description="Deathrattle: Summon a 1/1 Ember.",
    on_death=deathrattle,
)
