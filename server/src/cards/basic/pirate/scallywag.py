from ...base import CardDef
from ...base import DeathEvent
from ...base import Minion
from ....combat import CombatContext


def deathrattle(minion: Minion, event: DeathEvent, ctx: CombatContext) -> None:
    if ctx.is_self(minion, event.subject):
        ctx.summon("sky_pirate")


CARD = CardDef(
    id="scallywag",
    name="Scallywag",
    base_attack=2,
    base_health=1,
    tier=1,
    description="Deathrattle: Summon a 1/1 Pirate with Windfury.",
    on_death=deathrattle,
)
