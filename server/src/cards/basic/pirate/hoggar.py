from ...base import CardDef
from ...base import CombatStartEvent
from ...base import KillEvent
from ...base import Minion
from ....combat import CombatContext


def reset(minion: Minion, event: CombatStartEvent, ctx: CombatContext) -> None:
    minion.hoggar_summoned = False


def summon_copy(minion: Minion, event: KillEvent, ctx: CombatContext) -> None:
    if not ctx.is_self(minion, event.actor):
        return
    if getattr(minion, "hoggar_summoned", False):
        return
    minion.hoggar_summoned = True
    ctx.summon_copy(minion, after=minion)


CARD = CardDef(
    id="hoggar",
    name="Hoggar",
    base_attack=6,
    base_health=6,
    tier=6,
    description="The first time this kills a minion each combat, summon a copy of it.",
    on_combat_start=reset,
    on_kill=summon_copy,
)
