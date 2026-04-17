from ...base import CardDef
from ...base import Minion
from ...base import RoundStartEvent
from ....player import BuyContext


def prosper(minion: Minion, event: RoundStartEvent, ctx: BuyContext) -> None:
    gain = max(1, ctx.player.max_gold // 5)
    ctx.buff(minion, attack=gain, health=gain)


CARD = CardDef(
    id="goldgrub_baron",
    name="Goldgrub Baron",
    base_attack=5,
    base_health=5,
    tier=5,
    description="At the start of each round, gain +1/+1 per 5 maximum Gold (minimum +1/+1).",
    on_round_start=prosper,
)
