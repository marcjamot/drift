from ...base import AttackEvent
from ...base import CardDef
from ...base import Minion
from ....combat import CombatContext


def execute(minion: Minion, event: AttackEvent, ctx: CombatContext) -> None:
    if not ctx.is_self(minion, event.actor):
        return
    if event.target.health < event.target.max_health:
        ctx.deal_damage(event.target, max(0, event.target.health))


CARD = CardDef(
    id="mirror_assassin",
    name="Mirror Assassin",
    base_attack=8,
    base_health=3,
    tier=5,
    description="When this attacks a damaged minion, deal damage equal to its remaining Health.",
    on_attack=execute,
)
