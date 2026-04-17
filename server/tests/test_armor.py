import asyncio

from src.match.match import Match
from src.player.player import PlayerState


def test_damage_fully_absorbed_by_armor():
    player = PlayerState(player_id="p1", name="p1", armor=5)
    match = Match(match_id="armor-test", players=[player], seed=42)

    match.apply_player_damage(player, 3)

    assert player.armor == 2
    assert player.health == 40


def test_damage_exceeds_armor():
    player = PlayerState(player_id="p1", name="p1", armor=2)
    match = Match(match_id="armor-test", players=[player], seed=42)

    match.apply_player_damage(player, 5)

    assert player.armor == 0
    assert player.health == 37


def test_damage_with_zero_armor_hits_health():
    player = PlayerState(player_id="p1", name="p1", armor=0)
    match = Match(match_id="armor-test", players=[player], seed=42)

    match.apply_player_damage(player, 3)

    assert player.armor == 0
    assert player.health == 37


def test_armor_field_appears_in_snapshots():
    player = PlayerState(player_id="p1", name="p1", armor=5)
    opponent = PlayerState(player_id="p2", name="p2", armor=10, is_bot=True)
    match = Match(match_id="armor-test", players=[player, opponent], seed=42)
    sent = []

    async def capture(message: str) -> None:
        sent.append(message)

    async def send_state() -> None:
        import json

        match.register_sender(player.player_id, capture)
        await match.send_state(player.player_id)
        sent[0] = json.loads(sent[0])

    asyncio.run(send_state())

    assert player.to_dict(as_self=True)["armor"] == 5
    assert sent[0]["self"]["armor"] == 5
    assert {entry["player_id"]: entry["armor"] for entry in sent[0]["leaderboard"]} == {
        "p1": 5,
        "p2": 10,
    }
