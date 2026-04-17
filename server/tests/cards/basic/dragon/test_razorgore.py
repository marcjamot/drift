import random

from src.cards.catalog import CARD_CATALOG, SHOP_CARDS
from src.combat.engine import resolve_combat

from tests.conftest import card


def test_razorgore_is_in_shop_at_tier_four():
    shop_by_id = {card_def.id: card_def for card_def in SHOP_CARDS}
    assert "razorgore" in CARD_CATALOG
    assert shop_by_id["razorgore"].tier == 4


def test_razorgore_combat_start_attack_adds_friendly_dragon_count():
    razorgore = card("razorgore")
    result = resolve_combat(
        [razorgore, card("twilight_emissary"), card("chrono_dragon"), card("shield_bearer")],
        [],
        random.Random(42),
        1,
        1,
    )

    survivor = next(m for m in result["surviving_a"] if m["instance_id"] == razorgore.instance_id)
    assert survivor["attack"] == CARD_CATALOG["razorgore"].base_attack + 3
