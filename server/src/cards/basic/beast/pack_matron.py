from ...base import CardDef
from ...base import DeathEvent
from ...base import Minion
from ....combat import CombatContext


def deathrattle(minion: Minion, event: DeathEvent, ctx: CombatContext) -> None:
    if not ctx.is_self(minion, event.subject):
        return
    first = ctx.summon("cub", after=minion)
    ctx.summon("cub", after=first)


CARD = CardDef(
    id="pack_matron",
    name="Pack Matron",
    base_attack=4,
    base_health=4,
    tier=3,
    description="Deathrattle: Summon two 2/2 Cubs.",
    on_death=deathrattle,
)
