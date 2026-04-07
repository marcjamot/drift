from ..base import CardDef
from ..base import AttackEvent
from ..base import Minion
from ...combat import CombatContext


def strip_target(minion: Minion, event: AttackEvent, ctx: CombatContext) -> None:
    if not ctx.is_self(minion, event.actor):
        return
    event.target.keywords.clear()
    event.target.divine_shield = False


CARD = CardDef(
    id="frost_herald",
    name="Frost Herald",
    base_attack=3,
    base_health=7,
    tier=4,
    description="When this attacks, remove the target's keywords and Divine Shield.",
    on_attack=strip_target,
)
