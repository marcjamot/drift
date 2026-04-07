from ..base import CardDef
from ..base import Minion
from ..base import SpawnEvent
from ...combat import CombatContext


def reward_summon(minion: Minion, event: SpawnEvent, ctx: CombatContext) -> None:
    if ctx.is_self(minion, event.subject):
        return
    if ctx.is_friendly(minion, event.subject, event.subject_side):
        ctx.buff(event.subject, attack=2, health=1)


CARD = CardDef(
    id="blood_archivist",
    name="Blood Archivist",
    base_attack=4,
    base_health=5,
    tier=4,
    description="After a friendly minion is summoned in combat, give it +2/+1.",
    on_spawn=reward_summon,
)
