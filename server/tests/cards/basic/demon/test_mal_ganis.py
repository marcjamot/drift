import random

from src.cards.catalog import CARD_CATALOG, SHOP_CARDS
from src.combat.engine import resolve_combat

from tests.conftest import card


def test_mal_ganis_is_in_shop_at_tier_five():
    shop_by_id = {card_def.id: card_def for card_def in SHOP_CARDS}
    assert "mal_ganis" in CARD_CATALOG
    assert shop_by_id["mal_ganis"].tier == 5


def test_mal_ganis_buffs_demons_only_at_combat_start():
    boss = card("imp_gang_boss")
    mal_ganis = card("mal_ganis")
    neutral = card("shield_bearer")

    result = resolve_combat([boss, mal_ganis, neutral], [], random.Random(42), 1, 1)
    survivors = {m["instance_id"]: m for m in result["surviving_a"]}

    assert survivors[boss.instance_id]["attack"] == CARD_CATALOG["imp_gang_boss"].base_attack + 2
    assert survivors[boss.instance_id]["health"] == CARD_CATALOG["imp_gang_boss"].base_health + 2
    assert survivors[mal_ganis.instance_id]["attack"] == CARD_CATALOG["mal_ganis"].base_attack + 2
    assert survivors[neutral.instance_id]["attack"] == CARD_CATALOG["shield_bearer"].base_attack
