from ...base import CardDef
from ...base import Minion
from ...base import PlayEvent
from ...base import Tribe
from ....player import BuyContext


def battlecry(minion: Minion, event: PlayEvent, ctx: BuyContext) -> None:
    if not ctx.is_self(minion, event.subject):
        return
    if any(card.tribe == Tribe.DRAGON for card in ctx.player.hand):
        ctx.buff(minion, attack=2, health=2)


CARD = CardDef(
    id="twilight_emissary",
    name="Twilight Emissary",
    base_attack=2,
    base_health=3,
    tier=3,
    description="Battlecry: If you have a Dragon in hand, gain +2/+2.",
    on_play=battlecry,
)
