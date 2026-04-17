from ...base import CardDef
from ...base import Minion
from ...base import RoundStartEvent
from ....player import BuyContext


def grow_each_round(minion: Minion, event: RoundStartEvent, ctx: BuyContext) -> None:
    ctx.buff(minion, attack=1, health=0)


CARD = CardDef(
    id="tavern_troublemaker",
    name="Tavern Troublemaker",
    base_attack=2,
    base_health=2,
    tier=1,
    description="At the start of each round, gain +1 Attack.",
    on_round_start=grow_each_round,
)
