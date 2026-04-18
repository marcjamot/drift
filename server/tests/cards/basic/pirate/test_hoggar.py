import random

from src.cards.catalog import CARD_CATALOG, SHOP_CARDS
from src.combat.engine import resolve_combat

from tests.conftest import bare, card


def test_hoggar_is_in_shop_at_tier_six():
    shop_by_id = {card_def.id: card_def for card_def in SHOP_CARDS}
    assert "hoggar" in CARD_CATALOG
    assert shop_by_id["hoggar"].tier == 6


def test_hoggar_summons_only_one_copy_after_multiple_kills():
    hoggar = card("hoggar", keywords={"cleave"}, health=20, max_health=20)
    result = resolve_combat(
        [hoggar],
        [bare(0, 1), bare(0, 1), bare(0, 1)],
        random.Random(42),
        1,
        1,
    )

    hoggar_summons = [
        event for event in result["events"]
        if event["type"] == "summon" and event["card_id"] == "hoggar"
    ]
    assert len(hoggar_summons) == 1
