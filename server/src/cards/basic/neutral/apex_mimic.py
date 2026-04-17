from ...base import CardDef
from ...base import CombatStartEvent
from ...base import Minion
from ....combat import CombatContext


def mimic(minion: Minion, event: CombatStartEvent, ctx: CombatContext) -> None:
    targets = [m for m in ctx.friendly_board if m.instance_id != minion.instance_id]
    if not targets:
        return
    source = max(targets, key=lambda m: (m.attack, m.health, m.instance_id))
    minion.keywords.update(source.keywords)
    if source.divine_shield:
        minion.divine_shield = True


CARD = CardDef(
    id="apex_mimic",
    name="Apex Mimic",
    base_attack=10,
    base_health=10,
    tier=6,
    description="At combat start, copy the keywords of your highest-Attack other minion.",
    on_combat_start=mimic,
)
