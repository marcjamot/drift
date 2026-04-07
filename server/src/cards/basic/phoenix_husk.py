from ..base import CardDef
from ..base import DeathEvent
from ..base import Minion
from ...combat import CombatContext


def rebirth(minion: Minion, event: DeathEvent, ctx: CombatContext) -> None:
    if ctx.is_self(minion, event.subject):
        ctx.summon("phoenix")


CARD = CardDef(
    id="phoenix_husk",
    name="Phoenix Husk",
    base_attack=4,
    base_health=4,
    tier=5,
    description="Deathrattle: Summon a 6/2 Phoenix.",
    on_death=rebirth,
)
