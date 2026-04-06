from ..base import CardDef
from ..base import Minion
from ..base import PlayEvent
from ...player import BuyContext


def battlecry(minion: Minion, event: PlayEvent, ctx: BuyContext) -> None:
    if not ctx.is_self(minion, event.subject):
        return
    targets: list[Minion] = [m for m in ctx.player.board if m.instance_id != minion.instance_id]
    if targets:
        target: Minion = ctx.rng.choice(targets)
        ctx.buff(target, attack=1, health=1)

CARD = CardDef(
    id="rally_hound",
    name="Rally Hound",
    base_attack=2,
    base_health=2,
    tier=2,
    description="Battlecry: Give a random friendly minion +1/+1.",
    on_play=battlecry,
)
