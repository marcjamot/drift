from src.cards.catalog import CARD_CATALOG, SHOP_CARDS
from src.match.actions import play

from tests.conftest import card, make_player, make_pool, make_rng


def test_twilight_emissary_is_in_shop_at_tier_three():
    shop_by_id = {card_def.id: card_def for card_def in SHOP_CARDS}
    assert "twilight_emissary" in CARD_CATALOG
    assert shop_by_id["twilight_emissary"].tier == 3


def test_twilight_emissary_buffs_with_dragon_in_hand_on_play():
    player = make_player()
    player.hand = [card("twilight_emissary"), card("chrono_dragon")]

    assert play(player, 0, make_pool(), make_rng()) == {"ok": True}
    emissary = player.board[0]
    assert emissary.attack == CARD_CATALOG["twilight_emissary"].base_attack + 2
    assert emissary.health == CARD_CATALOG["twilight_emissary"].base_health + 2


def test_twilight_emissary_does_not_buff_without_dragon_in_hand_on_play():
    player = make_player()
    player.hand = [card("twilight_emissary"), card("shield_bearer")]

    assert play(player, 0, make_pool(), make_rng()) == {"ok": True}
    emissary = player.board[0]
    assert emissary.attack == CARD_CATALOG["twilight_emissary"].base_attack
    assert emissary.health == CARD_CATALOG["twilight_emissary"].base_health
