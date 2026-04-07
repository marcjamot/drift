from ..base import CardDef
from ..base import Minion
from ..base import PlayEvent
from ...player import BuyContext


def battlecry(minion: Minion, event: PlayEvent, ctx: BuyContext) -> None:
    if not ctx.is_self(minion, event.subject):
        return
    targets = [m for m in ctx.player.board if m.instance_id != minion.instance_id]
    if targets:
        ctx.buff(ctx.rng.choice(targets), attack=1, health=1)


CARD = CardDef(
    id="banner_pup",
    name="Banner Pup",
    base_attack=2,
    base_health=3,
    tier=2,
    description="Battlecry: Give another random friendly minion +1/+1.",
    on_play=battlecry,
)
