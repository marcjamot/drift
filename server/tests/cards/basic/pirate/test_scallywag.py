import random

from src.cards.base import Tribe
from src.cards.catalog import CARD_CATALOG, SHOP_CARDS
from src.combat.engine import resolve_combat

from tests.conftest import bare, card


def test_scallywag_is_in_shop_at_tier_one():
    shop_by_id = {card_def.id: card_def for card_def in SHOP_CARDS}
    assert "scallywag" in CARD_CATALOG
    assert shop_by_id["scallywag"].tier == 1


def test_scallywag_death_summons_windfury_pirate():
    result = resolve_combat(
        [card("scallywag"), bare(0, 10)],
        [bare(2, 10)],
        random.Random(42),
        1,
        1,
    )

    token = next(
        event["minion"]
        for event in result["events"]
        if event["type"] == "summon" and event["card_id"] == "sky_pirate"
    )
    assert token["attack"] == 1
    assert token["health"] == 1
    assert token["tribe"] == Tribe.PIRATE
    assert "windfury" in token["keywords"]
