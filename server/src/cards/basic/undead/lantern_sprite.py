from ...base import CardDef
from ...base import DeathEvent
from ...base import Minion
from ....combat import CombatContext


def deathrattle(minion: Minion, event: DeathEvent, ctx: CombatContext) -> None:
    if not ctx.is_self(minion, event.subject):
        return
    targets = [m for m in ctx.friendly_board if m.instance_id != minion.instance_id]
    if not targets:
        return
    target = targets[0]
    target.divine_shield = True


CARD = CardDef(
    id="lantern_sprite",
    name="Lantern Sprite",
    base_attack=2,
    base_health=2,
    tier=2,
    description="Deathrattle: Give the left-most other friendly minion Divine Shield.",
    on_death=deathrattle,
)
