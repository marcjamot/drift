import importlib
import pkgutil

from src.cards.base import TRIBES
from src.cards import basic, tokens
from src.cards.catalog import CARD_CATALOG
from src.cards.tokens import TOKEN_CARDS


def _card_modules():
    for package in (basic, tokens):
        for module_info in pkgutil.walk_packages(package.__path__, f"{package.__name__}."):
            module = importlib.import_module(module_info.name)
            if hasattr(module, "CARD"):
                yield module


def test_all_catalog_cards_have_valid_tribe():
    for card in CARD_CATALOG.values():
        assert card.tribe
        assert card.tribe in TRIBES


def test_all_token_cards_have_valid_tribe():
    for card in TOKEN_CARDS:
        assert card.tribe
        assert card.tribe in TRIBES


def test_card_tribes_match_parent_folder():
    for module in _card_modules():
        expected_tribe = module.__name__.split(".")[-2]
        assert module.CARD.tribe == expected_tribe


def test_minion_inherits_tribe_from_card_def():
    minion = CARD_CATALOG["iron_automaton"].create_instance()
    assert minion.tribe == "mech"


def test_minion_to_dict_includes_tribe():
    minion = CARD_CATALOG["stone_golem"].create_instance()
    assert minion.to_dict()["tribe"] == "neutral"
