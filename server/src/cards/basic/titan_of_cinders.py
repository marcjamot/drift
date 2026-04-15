from ..base import CardDef, Hook
from ..base import DeathEvent
from ..base import Minion
from ...combat import CombatContext


def chain_blast(minion: Minion, event: DeathEvent, ctx: CombatContext) -> None:
    if ctx.is_enemy(minion, event.subject, event.subject_side):
        for enemy in list(ctx.enemy_board):
            ctx.deal_damage(enemy, 1)


CARD = CardDef(
    id="titan_of_cinders",
    name="Titan of Cinders",
    base_attack=8,
    base_health=10,
    tier=6,
    keywords=["taunt"],
    description="Taunt. Whenever an enemy minion dies, deal 1 damage to all enemy minions.",
    on_death=Hook(after=chain_blast),
)
