from ...base import CardDef, Hook
from ...base import DeathEvent
from ...base import Minion
from ....combat import CombatContext


def forge_souls(minion: Minion, event: DeathEvent, ctx: CombatContext) -> None:
    if ctx.is_self(minion, event.subject):
        return
    if ctx.is_friendly(minion, event.subject, event.subject_side):
        ctx.summon("ember")


CARD = CardDef(
    id="soul_foundry",
    name="Soul Foundry",
    base_attack=6,
    base_health=12,
    tier=6,
    description="Whenever another friendly minion dies, summon a 1/1 Ember.",
    on_death=Hook(after=forge_souls),
)
