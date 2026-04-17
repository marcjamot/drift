from ...base import CardDef
from ...base import DeathEvent
from ...base import Minion
from ....combat import CombatContext


def deathrattle(minion: Minion, event: DeathEvent, ctx: CombatContext) -> None:
    if not ctx.is_self(minion, event.subject):
        return
    for enemy in list(ctx.enemy_board):
        ctx.deal_damage(enemy, 1)

CARD = CardDef(
    id="bomb_bot",
    name="Bomb Bot",
    base_attack=2,
    base_health=1,
    tier=1,
    description="Deathrattle: Deal 1 damage to all enemy minions.",
    on_death=deathrattle,
)
