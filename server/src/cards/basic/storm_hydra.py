from ..base import AttackEvent
from ..base import CardDef
from ..base import Minion
from ...combat import CombatContext


def splash(minion: Minion, event: AttackEvent, ctx: CombatContext) -> None:
    if not ctx.is_self(minion, event.actor):
        return
    for enemy in list(ctx.enemy_board):
        if enemy.instance_id != event.target.instance_id:
            ctx.deal_damage(enemy, 1)


CARD = CardDef(
    id="storm_hydra",
    name="Storm Hydra",
    base_attack=7,
    base_health=5,
    tier=5,
    description="After this attacks, deal 1 damage to every other enemy minion.",
    on_attack=splash,
)
