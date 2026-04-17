from ...base import CardDef
from ...base import CombatStartEvent
from ...base import Minion
from ...base import Tribe
from ....combat import CombatContext


KEYWORDS = ("divine_shield", "poisonous", "windfury")


def adapt_murlocs(minion: Minion, event: CombatStartEvent, ctx: CombatContext) -> None:
    keyword = ctx.rng.choice(KEYWORDS)
    for friendly in ctx.friendly_board:
        if friendly.tribe == Tribe.MURLOC:
            ctx.add_keyword(friendly, keyword)
            if keyword == "divine_shield":
                friendly.divine_shield = True


CARD = CardDef(
    id="megasaur",
    name="Megasaur",
    base_attack=5,
    base_health=5,
    tier=5,
    description="At combat start, give your Murlocs a random keyword.",
    on_combat_start=adapt_murlocs,
)
