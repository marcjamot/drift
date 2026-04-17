from ...base import CardDef
from ...base import CombatStartEvent
from ...base import DamageEvent
from ...base import Minion
from ....combat import CombatContext


def reset(minion: Minion, event: CombatStartEvent, ctx: CombatContext) -> None:
    minion.sky_duelist_triggered = False


def empower(minion: Minion, event: DamageEvent, ctx: CombatContext) -> None:
    if not ctx.is_self(minion, event.subject):
        return
    if event.amount != 0:
        return
    if getattr(minion, "sky_duelist_triggered", False):
        return
    minion.sky_duelist_triggered = True
    ctx.buff(minion, attack=2)


CARD = CardDef(
    id="sky_duelist",
    name="Sky Duelist",
    base_attack=5,
    base_health=2,
    tier=3,
    keywords=["divine_shield"],
    description="Divine Shield. The first time this blocks damage with Divine Shield, gain +2 Attack.",
    on_combat_start=reset,
    on_damage=empower,
)
