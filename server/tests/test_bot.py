import random
from dataclasses import dataclass

from src.cards.catalog import SHOP_CARDS
from src.cards.pool import CardPool
from src.match.bot import run_bot_buy_phase
from src.player.player import BOARD_SIZE, PlayerState


@dataclass
class BotMatch:
    round: int
    pool: CardPool
    rng: random.Random


def make_match(round_num: int = 1) -> BotMatch:
    return BotMatch(
        round=round_num,
        pool=CardPool(SHOP_CARDS, random.Random(42)),
        rng=random.Random(42),
    )


def make_card(card_id: str):
    return next(card for card in SHOP_CARDS if card.id == card_id).create_instance()


def test_bot_upgrades_with_enough_gold_and_cheap_upgrade_cost():
    player = PlayerState(
        player_id="bot",
        name="Bot",
        gold=10,
        tavern_tier=2,
        upgrade_cost=4,
        shop=[],
        is_bot=True,
    )

    run_bot_buy_phase(player, make_match(round_num=4))

    assert player.tavern_tier == 3
    assert player.gold == 6
    assert player.locked


def test_bot_does_not_play_more_cards_when_board_is_full():
    player = PlayerState(
        player_id="bot",
        name="Bot",
        gold=3,
        board=[make_card("stone_golem") for _ in range(BOARD_SIZE)],
        hand=[make_card("hunting_hound")],
        shop=[make_card("ashen_rat")],
        is_bot=True,
    )

    run_bot_buy_phase(player, make_match())

    assert len(player.board) == BOARD_SIZE
    assert [card.card_id for card in player.hand] == ["hunting_hound"]
    assert player.shop[0] is not None
    assert player.locked


def test_bot_locks_and_returns_without_looping():
    player = PlayerState(
        player_id="bot",
        name="Bot",
        gold=2,
        shop=[],
        is_bot=True,
    )

    run_bot_buy_phase(player, make_match())

    assert player.locked
    assert player.gold == 2


def test_bot_with_zero_gold_does_nothing_and_locks_immediately():
    player = PlayerState(
        player_id="bot",
        name="Bot",
        gold=0,
        upgrade_cost=0,
        shop=[make_card("stone_golem")],
        hand=[make_card("hunting_hound")],
        is_bot=True,
    )

    run_bot_buy_phase(player, make_match())

    assert player.tavern_tier == 1
    assert player.gold == 0
    assert [card.card_id for card in player.hand] == ["hunting_hound"]
    assert player.shop[0] is not None
    assert player.locked


def test_bot_prefers_buying_tribal_match_over_same_cost_neutral_card():
    player = PlayerState(
        player_id="bot",
        name="Bot",
        gold=3,
        board=[make_card("hunting_hound"), make_card("ashen_rat")],
        shop=[make_card("stone_golem"), make_card("ashen_rat")],
        is_bot=True,
    )

    run_bot_buy_phase(player, make_match())

    assert [card.card_id for card in player.board] == [
        "hunting_hound",
        "ashen_rat",
        "ashen_rat",
    ]
    assert player.shop[0] is not None
    assert player.shop[1] is None
    assert player.locked
