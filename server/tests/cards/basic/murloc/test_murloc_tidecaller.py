from src.cards.catalog import CARD_CATALOG, SHOP_CARDS
from src.player import BuyContext

from tests.conftest import card, make_player, make_rng


def test_murloc_tidecaller_is_in_shop_at_tier_one():
    shop_by_id = {card_def.id: card_def for card_def in SHOP_CARDS}
    assert "murloc_tidecaller" in CARD_CATALOG
    assert shop_by_id["murloc_tidecaller"].tier == 1


def test_murloc_tidecaller_gains_attack_per_murloc_spawn():
    player = make_player()
    tidecaller = card("murloc_tidecaller")
    player.board = [tidecaller]
    ctx = BuyContext(player=player, rng=make_rng())

    for _ in range(3):
        spawned = ctx.summon_to_board("megasaur")
        assert spawned is not None

    assert tidecaller.attack == CARD_CATALOG["murloc_tidecaller"].base_attack + 3
