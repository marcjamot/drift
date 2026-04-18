
from src.cards.catalog import CARD_CATALOG
from src.match import actions
from src.match.triples import auto_pick_discovers, check_triple
from src.player.player import BUY_COST, PlayerState

from .conftest import make_player, make_pool, make_rng


def test_three_cards_in_hand_become_golden_and_trigger_discover():
    player = make_player()
    pool = make_pool()

    player.hand = [CARD_CATALOG["shield_bearer"].create_instance() for _ in range(3)]

    actions.check_triple(player, pool, make_rng())

    assert len(player.hand) == 1
    assert player.hand[0].card_id == "shield_bearer"
    assert player.hand[0].golden
    assert player.pending_discover is not None
    assert len(player.pending_discover) == 3


def test_buying_third_copy_with_two_in_hand_and_one_on_board_triggers_triple():
    player = make_player(gold=BUY_COST)
    pool = make_pool()
    player.hand = [CARD_CATALOG["shield_bearer"].create_instance()]
    player.board = [CARD_CATALOG["shield_bearer"].create_instance()]
    player.shop = [CARD_CATALOG["shield_bearer"].create_instance()]

    result = actions.buy(player, 0, pool, make_rng())

    assert result == {"ok": True}
    assert player.board == []
    assert len(player.hand) == 1
    assert player.hand[0].golden
    assert player.pending_discover is not None


def test_golden_minion_has_doubled_base_stats():
    player = make_player()
    pool = make_pool()
    base = CARD_CATALOG["shield_bearer"]
    player.hand = [base.create_instance() for _ in range(3)]

    actions.check_triple(player, pool, make_rng())

    golden = player.hand[0]
    assert golden.attack == base.base_attack * 2
    assert golden.health == base.base_health * 2
    assert golden.max_health == base.base_health * 2
    assert golden.golden


def test_discover_offers_three_cards_from_next_tavern_tier():
    player = make_player(tier=1)
    pool = make_pool()
    player.hand = [CARD_CATALOG["shield_bearer"].create_instance() for _ in range(3)]

    actions.check_triple(player, pool, make_rng())

    assert player.pending_discover is not None
    assert len(player.pending_discover) == 3
    assert {card.tier for card in player.pending_discover} == {2}


def test_returned_triple_copies_increase_original_card_pool_count_by_three():
    player = make_player()
    pool = make_pool()
    player.hand = [CARD_CATALOG["shield_bearer"].create_instance() for _ in range(3)]
    before = pool.available.count("shield_bearer")

    actions.check_triple(player, pool, make_rng())

    assert pool.available.count("shield_bearer") == before + 3


def test_bot_auto_picks_discover_and_does_not_leave_pending():
    bot = PlayerState(player_id="bot", name="Bot", is_bot=True)
    pool = make_pool()
    bot.pending_discover = [CARD_CATALOG["shield_bearer"].create_instance() for _ in range(3)]
    first_option_id = bot.pending_discover[0].card_id

    auto_pick_discovers(bot, pool, make_rng())

    assert bot.pending_discover is None
    assert any(m.card_id == first_option_id for m in bot.hand)


def test_human_triple_leaves_pending_discover_for_client():
    """For human players, triple resolution leaves pending_discover for the client to pick."""
    player = make_player()
    pool = make_pool()
    player.hand = [CARD_CATALOG["shield_bearer"].create_instance() for _ in range(3)]

    check_triple(player, pool, make_rng())

    # Human's discover is NOT auto-resolved — client sends discover_pick
    assert player.pending_discover is not None
    assert len(player.pending_discover) == 3


def test_triple_does_not_trigger_on_two_copies():
    player = make_player()
    pool = make_pool()
    player.hand = [CARD_CATALOG["shield_bearer"].create_instance() for _ in range(2)]

    actions.check_triple(player, pool, make_rng())

    assert len(player.hand) == 2
    assert not any(card.golden for card in player.hand)
    assert player.pending_discover is None
