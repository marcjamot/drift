from ...base import CardDef
from ...base import CombatStartEvent
from ...base import Minion
from ...base import Tribe
from ....combat import CombatContext


def rally_demons(minion: Minion, event: CombatStartEvent, ctx: CombatContext) -> None:
    for friendly in ctx.friendly_board:
        if friendly.tribe == Tribe.DEMON:
            ctx.buff(friendly, attack=2, health=2)


CARD = CardDef(
    id="mal_ganis",
    name="Mal'Ganis",
    base_attack=9,
    base_health=7,
    tier=5,
    description="At combat start, give your Demons +2/+2.",
    on_combat_start=rally_demons,
)
