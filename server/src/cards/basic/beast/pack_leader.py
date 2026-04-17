from ...base import CardDef
from ...base import Minion
from ...base import PlayEvent
from ...base import Tribe
from ....player import BuyContext


def battlecry(minion: Minion, event: PlayEvent, ctx: BuyContext) -> None:
    if not ctx.is_self(minion, event.subject):
        return
    for friendly in list(ctx.player.board):
        if friendly.instance_id != minion.instance_id and friendly.tribe == Tribe.BEAST:
            ctx.buff(friendly, attack=1)


CARD = CardDef(
    id="pack_leader",
    name="Pack Leader",
    base_attack=3,
    base_health=3,
    tier=2,
    description="Battlecry: Give your other Beasts +1 Attack.",
    on_play=battlecry,
)
