import asyncio
import json

from src.cards.catalog import CARD_CATALOG
from src.match import actions
from src.match.match import Match
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


def test_bot_auto_picks_discover_option_zero_without_sending_offer():
    bot = PlayerState(
        player_id="bot",
        name="Bot",
        gold=BUY_COST,
        max_gold=BUY_COST,
        hand=[CARD_CATALOG["shield_bearer"].create_instance()],
        board=[CARD_CATALOG["shield_bearer"].create_instance()],
        shop=[CARD_CATALOG["shield_bearer"].create_instance()],
        is_bot=True,
    )
    match = Match("m1", [bot], seed=42)
    match.phase = "buy"
    match._current_phase = match._buy_phase
    sent: list[dict] = []

    async def send(raw: str) -> None:
        sent.append(json.loads(raw))

    match.register_sender("bot", send)

    result = asyncio.run(match.handle_action("bot", {"type": "buy", "shop_index": 0}))

    assert result == {"ok": True}
    assert bot.pending_discover is None
    assert not any(msg["type"] == "discover_options" for msg in sent)
    assert len(bot.hand) == 2
    assert bot.hand[0].golden
    assert bot.hand[1].tier == 2


def test_human_triple_sends_discover_options_message():
    player = PlayerState(
        player_id="p1",
        name="p1",
        gold=BUY_COST,
        max_gold=BUY_COST,
        hand=[CARD_CATALOG["shield_bearer"].create_instance()],
        board=[CARD_CATALOG["shield_bearer"].create_instance()],
        shop=[CARD_CATALOG["shield_bearer"].create_instance()],
    )
    match = Match("m1", [player], seed=42)
    match.phase = "buy"
    match._current_phase = match._buy_phase
    sent: list[dict] = []

    async def send(raw: str) -> None:
        sent.append(json.loads(raw))

    match.register_sender("p1", send)

    result = asyncio.run(match.handle_action("p1", {"type": "buy", "shop_index": 0}))

    assert result == {"ok": True}
    discover_messages = [msg for msg in sent if msg["type"] == "discover_options"]
    assert len(discover_messages) == 1
    assert len(discover_messages[0]["options"]) == 3
    assert {card["tier"] for card in discover_messages[0]["options"]} == {2}


def test_triple_does_not_trigger_on_two_copies():
    player = make_player()
    pool = make_pool()
    player.hand = [CARD_CATALOG["shield_bearer"].create_instance() for _ in range(2)]

    actions.check_triple(player, pool, make_rng())

    assert len(player.hand) == 2
    assert not any(card.golden for card in player.hand)
    assert player.pending_discover is None
