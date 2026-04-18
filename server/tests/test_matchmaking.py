import asyncio
import json

from src.matchmaking.matchmaker import MATCH_SIZE, Matchmaker
from src.player import PlayerState
from src.match import Match


async def _capture(messages: list[dict], data: str) -> None:
    messages.append(json.loads(data))


def _sender(messages: list[dict]):
    async def send(data: str) -> None:
        await _capture(messages, data)

    return send


async def _queue_player(matchmaker: Matchmaker, player_id: str, messages: list[dict]):
    return await matchmaker.queue(player_id, player_id, _sender(messages))


def test_single_player_queue_fills_with_seven_bots():
    async def run():
        messages: list[dict] = []
        matchmaker = Matchmaker(auto_start_matches=False)

        queued_match = await _queue_player(matchmaker, "p1", messages)
        assert queued_match is None

        match = await matchmaker.fill_pending_queue()
        assert match is not None
        assert sum(1 for p in match.players.values() if not p.is_bot) == 1
        assert sum(1 for p in match.players.values() if p.is_bot) == 7
        assert messages[-1]["queued_count"] == 1
        assert messages[-1]["total_slots"] == MATCH_SIZE
        assert messages[-1]["can_skip_wait"] is True

    asyncio.run(run())


def test_two_players_queue_into_same_match_with_six_bots():
    async def run():
        p1_messages: list[dict] = []
        p2_messages: list[dict] = []
        matchmaker = Matchmaker(auto_start_matches=False)

        await _queue_player(matchmaker, "p1", p1_messages)
        await _queue_player(matchmaker, "p2", p2_messages)
        match = await matchmaker.fill_pending_queue()

        assert match is not None
        assert sum(1 for p in match.players.values() if not p.is_bot) == 2
        assert sum(1 for p in match.players.values() if p.is_bot) == 6
        assert matchmaker.get_match_for_player("p1") is match
        assert matchmaker.get_match_for_player("p2") is match
        assert p1_messages[-1]["queued_count"] == 2
        assert p2_messages[-1]["queued_count"] == 2
        assert p1_messages[-1]["can_skip_wait"] is False
        assert p2_messages[-1]["can_skip_wait"] is False

    asyncio.run(run())


def test_eight_players_queue_starts_immediately_with_no_bots():
    async def run():
        matchmaker = Matchmaker(auto_start_matches=False)
        messages = {f"p{i}": [] for i in range(8)}
        match = None

        for player_id, player_messages in messages.items():
            match = await _queue_player(matchmaker, player_id, player_messages)

        assert match is not None
        assert sum(1 for p in match.players.values() if not p.is_bot) == 8
        assert sum(1 for p in match.players.values() if p.is_bot) == 0

    asyncio.run(run())


def test_human_players_receive_distinct_state_snapshots():
    async def run():
        p1_messages: list[dict] = []
        p2_messages: list[dict] = []
        players = [
            PlayerState(player_id="p1", name="p1", is_bot=False),
            PlayerState(player_id="p2", name="p2", is_bot=False),
            *[
                PlayerState(player_id=f"bot{i}", name=f"bot{i}", is_bot=True)
                for i in range(6)
            ],
        ]
        match = Match("state-test", players, seed=42)
        match.register_sender("p1", _sender(p1_messages))
        match.register_sender("p2", _sender(p2_messages))
        match._compute_combat_pairs()

        await match.send_state("p1")
        await match.send_state("p2")

        assert p1_messages[-1]["self"]["player_id"] == "p1"
        assert p2_messages[-1]["self"]["player_id"] == "p2"
        assert p1_messages[-1]["self"]["player_id"] != p2_messages[-1]["self"]["player_id"]

    asyncio.run(run())


def test_pairing_gives_each_human_one_unique_opponent_per_round():
    humans = [
        PlayerState(player_id=f"p{i}", name=f"p{i}", is_bot=False)
        for i in range(4)
    ]
    bots = [
        PlayerState(player_id=f"bot{i}", name=f"bot{i}", is_bot=True)
        for i in range(4)
    ]
    match = Match("pairing-test", [*humans, *bots], seed=42)

    for _round in range(5):
        match._compute_combat_pairs()
        human_opponents = {
            player.player_id: match._combat_pairs[player.player_id]
            for player in humans
        }

        assert len(human_opponents) == len(humans)
        assert len(set(human_opponents.values())) == len(humans)
