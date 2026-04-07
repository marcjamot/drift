from ..base import CardDef
from ..base import DeathEvent
from ..base import Minion
from ...combat import CombatContext


def deathrattle(minion: Minion, event: DeathEvent, ctx: CombatContext) -> None:
    if not ctx.is_self(minion, event.subject):
        return
    if ctx.enemy_board:
        ctx.deal_damage(ctx.enemy_board[0], 2)


CARD = CardDef(
    id="siege_golem",
    name="Siege Golem",
    base_attack=5,
    base_health=6,
    tier=4,
    keywords=["taunt"],
    description="Taunt. Deathrattle: Deal 2 damage to the left-most enemy minion.",
    on_death=deathrattle,
)
