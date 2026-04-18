import random

from src.cards.base import Tribe
from src.cards.catalog import CARD_CATALOG, SHOP_CARDS
from src.combat.engine import resolve_combat

from tests.conftest import card


def test_megasaur_is_in_shop_at_tier_five():
    shop_by_id = {card_def.id: card_def for card_def in SHOP_CARDS}
    assert "megasaur" in CARD_CATALOG
    assert shop_by_id["megasaur"].tier == 5


def test_megasaur_gives_all_murlocs_one_seeded_keyword():
    valid_keywords = {"divine_shield", "poisonous", "windfury"}

    result = resolve_combat(
        [card("megasaur"), card("murloc_tidecaller")],
        [],
        random.Random(1),
        1,
        1,
    )
    first_keywords = [
        set(m["keywords"]) & valid_keywords
        for m in result["surviving_a"]
        if m["tribe"] == Tribe.MURLOC
    ]

    assert first_keywords
    assert all(keywords == {"divine_shield"} for keywords in first_keywords)

    result = resolve_combat(
        [card("megasaur"), card("murloc_tidecaller")],
        [],
        random.Random(1),
        1,
        1,
    )
    repeated_keywords = [
        set(m["keywords"]) & valid_keywords
        for m in result["surviving_a"]
        if m["tribe"] == Tribe.MURLOC
    ]
    assert repeated_keywords == first_keywords

    result = resolve_combat(
        [card("megasaur"), card("murloc_tidecaller")],
        [],
        random.Random(5),
        1,
        1,
    )
    changed_keywords = [
        set(m["keywords"]) & valid_keywords
        for m in result["surviving_a"]
        if m["tribe"] == Tribe.MURLOC
    ]
    assert all(keywords == {"windfury"} for keywords in changed_keywords)
