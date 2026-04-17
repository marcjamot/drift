from ...base import CardDef
from ...base import CombatStartEvent
from ...base import Minion
from ...base import Tribe
from ....combat import CombatContext


def count_mechs(minion: Minion, event: CombatStartEvent, ctx: CombatContext) -> None:
    mechs = [m for m in ctx.friendly_board if m.tribe == Tribe.MECH]
    ctx.buff(minion, attack=len(mechs))


CARD = CardDef(
    id="deflect-o-bot",
    name="Deflect-o-Bot",
    base_attack=3,
    base_health=2,
    tier=3,
    description="At combat start, gain +1 Attack for each friendly Mech.",
    on_combat_start=count_mechs,
)
