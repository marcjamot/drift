from ...base import CardDef
from ...base import CombatStartEvent
from ...base import Minion
from ...base import Tribe
from ....combat import CombatContext


def pack_bonus(minion: Minion, event: CombatStartEvent, ctx: CombatContext) -> None:
    beasts = [m for m in ctx.friendly_board if m.tribe == Tribe.BEAST]
    if len(beasts) >= 3:
        ctx.buff(minion, attack=2)


CARD = CardDef(
    id="hunting_hound",
    name="Hunting Hound",
    base_attack=2,
    base_health=1,
    tier=1,
    description="At combat start, if you have 3 or more Beasts, gain +2 Attack this combat.",
    on_combat_start=pack_bonus,
)
