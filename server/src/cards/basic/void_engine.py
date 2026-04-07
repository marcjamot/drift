from ..base import CardDef
from ..base import DamageEvent
from ..base import Minion
from ...combat import CombatContext


def retaliate(minion: Minion, event: DamageEvent, ctx: CombatContext) -> None:
    if not ctx.is_self(minion, event.subject):
        return
    if event.amount <= 0:
        return
    for enemy in list(ctx.enemy_board):
        ctx.deal_damage(enemy, 2)


CARD = CardDef(
    id="void_engine",
    name="Void Engine",
    base_attack=6,
    base_health=6,
    tier=5,
    description="Whenever this takes damage, deal 2 damage to all enemy minions.",
    on_damage=retaliate,
)
