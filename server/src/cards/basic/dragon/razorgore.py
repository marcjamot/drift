from ...base import CardDef
from ...base import CombatStartEvent
from ...base import Minion
from ...base import Tribe
from ....combat import CombatContext


def count_dragons(minion: Minion, event: CombatStartEvent, ctx: CombatContext) -> None:
    dragons = [friendly for friendly in ctx.friendly_board if friendly.tribe == Tribe.DRAGON]
    ctx.buff(minion, attack=len(dragons))


CARD = CardDef(
    id="razorgore",
    name="Razorgore",
    base_attack=4,
    base_health=6,
    tier=4,
    description="At combat start, gain +1 Attack for each friendly Dragon.",
    on_combat_start=count_dragons,
)
