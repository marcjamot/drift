import random

from src.cards.catalog import CARD_CATALOG, SHOP_CARDS
from src.combat.engine import resolve_combat

from tests.conftest import bare, card


def test_imp_gang_boss_is_in_shop_at_tier_three():
    shop_by_id = {card_def.id: card_def for card_def in SHOP_CARDS}
    assert "imp_gang_boss" in CARD_CATALOG
    assert shop_by_id["imp_gang_boss"].tier == 3


def test_imp_gang_boss_summons_imp_on_damage():
    boss = card("imp_gang_boss")
    result = resolve_combat([boss], [bare(1, 20)], random.Random(42), 1, 1)

    assert any(
        event["type"] == "summon" and event["card_id"] == "imp"
        for event in result["events"]
    )


def test_imp_gang_boss_does_not_crash_when_board_is_full():
    full_board = [card("imp_gang_boss"), *[bare(0, 10) for _ in range(6)]]
    result = resolve_combat(full_board, [bare(1, 100)], random.Random(42), 1, 1)

    imp_summons = [
        event for event in result["events"]
        if event["type"] == "summon" and event["card_id"] == "imp"
    ]
    assert imp_summons == []
