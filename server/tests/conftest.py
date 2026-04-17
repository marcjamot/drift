"""Shared test helpers. Imported automatically by pytest for every test module."""
import random

import pytest

from src.cards.base import Minion
from src.cards.catalog import CARD_CATALOG, SHOP_CARDS
from src.cards.pool import CardPool
from src.player.player import PlayerState


def bare(attack: int, health: int, tier: int = 1, **kwargs) -> Minion:
    """Minimal minion with no card effects (card_id absent from catalog)."""
    return Minion(
        card_id="__test__",
        name="Test",
        description="",
        attack=attack,
        health=health,
        max_health=health,
        tier=tier,
        **kwargs,
    )


def card(card_id: str, **overrides) -> Minion:
    """Catalog minion with optional stat overrides."""
    m = CARD_CATALOG[card_id].create_instance()
    for k, v in overrides.items():
        setattr(m, k, v)
    return m


def make_player(
    player_id: str = "p1",
    gold: int = 10,
    tier: int = 1,
    round_num: int = 1,
) -> PlayerState:
    p = PlayerState(player_id=player_id, name=player_id)
    p.gold = gold
    p.max_gold = gold
    p.tavern_tier = tier
    p.start_round(round_num)
    p.gold = gold  # override the start_round gold with the passed-in value
    return p


def make_pool(seed: int = 0) -> CardPool:
    return CardPool(SHOP_CARDS, random.Random(seed))


def make_rng(seed: int = 42) -> random.Random:
    return random.Random(seed)
