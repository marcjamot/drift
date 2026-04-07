from ..base import CardDef
from ..base import CombatStartEvent
from ..base import Minion
from ..base import TargetEvent
from ...combat import CombatContext


def reset(minion: Minion, event: CombatStartEvent, ctx: CombatContext) -> None:
    minion.hex_used = False


def hex_target(minion: Minion, event: TargetEvent, ctx: CombatContext) -> None:
    if getattr(minion, "hex_used", False):
        return
    if not ctx.is_self(minion, event.actor):
        return
    minion.hex_used = True
    event.target.attack = min(1, event.target.attack)


CARD = CardDef(
    id="hex_dealer",
    name="Hex Dealer",
    base_attack=6,
    base_health=3,
    tier=4,
    description="The first enemy this targets each combat is reduced to 1 Attack.",
    on_combat_start=reset,
    on_target=hex_target,
)
