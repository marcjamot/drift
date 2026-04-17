from ...base import CardDef
from ...base import Minion
from ...base import PlayEvent
from ...base import Tribe
from ....player import BuyContext


def battlecry(minion: Minion, event: PlayEvent, ctx: BuyContext) -> None:
    if not ctx.is_self(minion, event.subject):
        return
    ctx.player.health -= 2
    for friendly in list(ctx.player.board):
        if friendly.tribe == Tribe.MECH:
            ctx.buff(friendly, attack=1, health=1)


CARD = CardDef(
    id="scrap_imp",
    name="Scrap Imp",
    base_attack=2,
    base_health=2,
    tier=2,
    description="Battlecry: Give your Mechs +1/+1 and take 2 damage.",
    on_play=battlecry,
)
