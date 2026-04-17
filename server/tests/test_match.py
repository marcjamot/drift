"""
Full match simulation tests.

These tests exercise the entire game loop — hero assignment, buy phases,
combat phases, damage, eliminations, and win condition — with eight bot
players so no WebSocket I/O is required.

asyncio.sleep is patched to a no-op so tests complete in milliseconds, and
BuyPhase.duration is set to 1 ms so the buy timer doesn't block.
"""
import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from src.match.match import Match
from src.match.phases.buy_phase import BuyPhase
from src.player.player import PlayerState


# ── helpers ────────────────────────────────────────────────────────────────────

def make_bots(n: int = 8) -> list[PlayerState]:
    bot_names = ["Grimshaw", "Vexara", "Ironpelt", "Solkar", "Brindle", "Mox", "Tesh", "Dross"]
    return [
        PlayerState(player_id=f"bot{i}", name=bot_names[i % len(bot_names)], is_bot=True)
        for i in range(n)
    ]


async def _run_match(seed: int = 42) -> Match:
    players = make_bots(8)
    match = Match(match_id="test-match", players=players, seed=seed)
    with (
        patch.object(BuyPhase, "duration", 0.001),
        patch("asyncio.sleep", new_callable=AsyncMock),
    ):
        await match.run()
    return match


# ── structural invariants ──────────────────────────────────────────────────────

class TestMatchCompletion:
    def test_match_reaches_game_over(self):
        match = asyncio.run(_run_match(seed=42))
        assert match.phase == "game_over"

    def test_exactly_one_survivor(self):
        match = asyncio.run(_run_match(seed=42))
        alive = [pid for pid in match.player_order if match.players[pid].health > 0]
        assert len(alive) == 1

    def test_winner_is_the_sole_survivor(self):
        match = asyncio.run(_run_match(seed=42))
        alive = [pid for pid in match.player_order if match.players[pid].health > 0]
        assert match.winner == alive[0]

    def test_winner_has_placement_one(self):
        match = asyncio.run(_run_match(seed=42))
        assert match.players[match.winner].placement == 1

    def test_all_players_have_placements(self):
        match = asyncio.run(_run_match(seed=42))
        for pid, player in match.players.items():
            assert player.placement is not None, f"{pid} has no placement"

    def test_placements_are_unique(self):
        match = asyncio.run(_run_match(seed=42))
        placements = [p.placement for p in match.players.values()]
        assert len(placements) == len(set(placements)), "Duplicate placements found"

    def test_placements_cover_one_through_eight(self):
        match = asyncio.run(_run_match(seed=42))
        placements = sorted(p.placement for p in match.players.values())
        assert placements == list(range(1, 9))


# ── determinism ───────────────────────────────────────────────────────────────

class TestDeterminism:
    def test_same_seed_produces_same_winner(self):
        m1 = asyncio.run(_run_match(seed=7))
        m2 = asyncio.run(_run_match(seed=7))
        assert m1.winner == m2.winner

    def test_same_seed_produces_same_placements(self):
        m1 = asyncio.run(_run_match(seed=7))
        m2 = asyncio.run(_run_match(seed=7))
        p1 = {pid: p.placement for pid, p in m1.players.items()}
        p2 = {pid: p.placement for pid, p in m2.players.items()}
        assert p1 == p2

    def test_different_seeds_can_produce_different_winners(self):
        winners = {asyncio.run(_run_match(seed=s)).winner for s in range(5)}
        assert len(winners) > 1, "Different seeds should sometimes produce different winners"


# ── hero assignment ───────────────────────────────────────────────────────────

class TestHeroAssignment:
    def test_every_bot_has_a_hero(self):
        match = asyncio.run(_run_match(seed=1))
        for pid, player in match.players.items():
            assert player.hero is not None, f"{pid} has no hero after match"


# ── elimination ordering ──────────────────────────────────────────────────────

class TestEliminations:
    def test_dead_players_have_nonzero_eliminated_round(self):
        match = asyncio.run(_run_match(seed=42))
        for pid, player in match.players.items():
            if pid != match.winner:
                assert player.eliminated_round is not None

    def test_winner_has_no_eliminated_round(self):
        match = asyncio.run(_run_match(seed=42))
        assert match.players[match.winner].eliminated_round is None

    def test_last_dead_has_lower_placement_than_winner(self):
        match = asyncio.run(_run_match(seed=42))
        non_winners = [p for pid, p in match.players.items() if pid != match.winner]
        assert all(p.placement > 1 for p in non_winners)

    def test_second_place_eliminated_latest(self):
        """Second place should have been eliminated in a later round than 8th place."""
        match = asyncio.run(_run_match(seed=42))
        by_placement = sorted(match.players.values(), key=lambda p: p.placement)
        second = by_placement[1]   # placement 2
        last = by_placement[-1]    # placement 8
        if second.eliminated_round and last.eliminated_round:
            assert second.eliminated_round >= last.eliminated_round
