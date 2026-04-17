from ...base import CardDef
from ...base import KillEvent
from ...base import Minion
from ....combat import CombatContext


def snowball(minion: Minion, event: KillEvent, ctx: CombatContext) -> None:
    if ctx.is_self(minion, event.actor):
        ctx.buff(minion, attack=3)


CARD = CardDef(
    id="chrono_dragon",
    name="Chrono Dragon",
    base_attack=9,
    base_health=8,
    tier=6,
    description="Whenever this kills a minion in combat, gain +3 Attack.",
    on_kill=snowball,
)
