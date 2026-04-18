from src.cards.base import TRIBES
from src.cards.catalog import CARD_CATALOG
from src.cards.tokens import TOKEN_CARDS


def test_all_catalog_cards_have_valid_tribe():
    for card_def in CARD_CATALOG.values():
        assert card_def.tribe, f"{card_def.id!r} has an empty tribe"
        assert card_def.tribe in TRIBES, f"{card_def.id!r} tribe {card_def.tribe!r} is not valid"


def test_all_token_cards_have_valid_tribe():
    for card_def in TOKEN_CARDS:
        assert card_def.tribe, f"{card_def.id!r} has an empty tribe"
        assert card_def.tribe in TRIBES, f"{card_def.id!r} tribe {card_def.tribe!r} is not valid"


def test_minion_inherits_tribe_from_card_def():
    minion = CARD_CATALOG["iron_automaton"].create_instance()
    assert minion.tribe == "mech"


def test_minion_to_dict_includes_tribe():
    minion = CARD_CATALOG["stone_golem"].create_instance()
    assert minion.to_dict()["tribe"] == "neutral"
