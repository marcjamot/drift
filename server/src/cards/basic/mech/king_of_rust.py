from ...base import CardDef
from ...base import CombatStartEvent
from ...base import Minion
from ....combat import CombatContext


def inspire(minion: Minion, event: CombatStartEvent, ctx: CombatContext) -> None:
    for friendly in list(ctx.friendly_board):
        if friendly.instance_id != minion.instance_id:
            ctx.buff(friendly, attack=2, health=2)


CARD = CardDef(
    id="king_of_rust",
    name="King of Rust",
    base_attack=7,
    base_health=9,
    tier=6,
    description="At combat start, give your other minions +2/+2.",
    on_combat_start=inspire,
)
