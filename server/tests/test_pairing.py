import random

from src.match.pairing import PairingService


def paired_players(pairs: list[tuple[str, str]]) -> list[str]:
    return [player for pair in pairs for player in pair]


def test_eight_players_make_four_pairs_with_no_duplicates():
    players = [f"p{i}" for i in range(8)]
    pairs = PairingService().pair(players, random.Random(42))

    paired = paired_players(pairs)
    assert len(pairs) == 4
    assert len(paired) == len(set(paired))
    assert set(paired) == set(players)


def test_seven_players_make_three_pairs_and_one_bye():
    players = [f"p{i}" for i in range(7)]
    pairs = PairingService().pair(players, random.Random(42))

    paired = paired_players(pairs)
    bye_players = set(players) - set(paired)
    assert len(pairs) == 3
    assert len(paired) == len(set(paired))
    assert len(bye_players) == 1


def test_two_players_make_one_pair():
    players = ["p0", "p1"]
    pairs = PairingService().pair(players, random.Random(42))

    assert len(pairs) == 1
    assert set(paired_players(pairs)) == set(players)


def test_one_player_makes_no_pairs():
    pairs = PairingService().pair(["p0"], random.Random(42))

    assert pairs == []


def test_pairing_is_deterministic_given_same_rng_seed():
    players = [f"p{i}" for i in range(8)]
    pairs_a = PairingService().pair(players, random.Random(42))
    pairs_b = PairingService().pair(players, random.Random(42))

    assert pairs_a == pairs_b
