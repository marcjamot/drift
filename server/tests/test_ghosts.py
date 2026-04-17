import asyncio
from unittest.mock import AsyncMock, patch

from src.match.match import Match
from src.match.phases.combat_phase import CombatPhase
from src.player.player import PlayerState
from .conftest import bare


def make_player(player_id: str, *, ghost: bool = False, eliminated_round: int | None = None) -> PlayerState:
    player = PlayerState(player_id=player_id, name=player_id, is_bot=True)
    if ghost:
        player.health = 0
        player.ghost = True
        player.eliminated_round = eliminated_round
        player.last_combat_board = [
            {
                "instance_id": f"{player_id}-ghost",
                "card_id": "__test__",
                "name": "Ghost",
                "description": "",
                "attack": 1,
                "health": 1,
                "max_health": 1,
                "tier": 1,
                "tribe": "neutral",
                "keywords": [],
                "divine_shield": False,
                "golden": False,
            }
        ]
    return player


def pairs_from_match(match: Match) -> set[frozenset[str]]:
    seen = set()
    pairs = set()
    for player_id, opponent_id in match._combat_pairs.items():
        pair = frozenset((player_id, opponent_id))
        if pair in seen:
            continue
        seen.add(pair)
        pairs.add(pair)
    return pairs


def test_pairing_with_three_alive_and_two_ghosts_fills_only_the_bye():
    players = [
        make_player("a"),
        make_player("b"),
        make_player("c"),
        make_player("g1", ghost=True, eliminated_round=3),
        make_player("g2", ghost=True, eliminated_round=4),
    ]
    match = Match(match_id="ghost-pairing", players=players, seed=42)

    match._compute_combat_pairs()

    alive = {"a", "b", "c"}
    ghost_pair_slots = [
        player_id
        for pair in pairs_from_match(match)
        for player_id in pair
        if player_id.startswith("g")
    ]
    assert all(player_id in match._combat_pairs for player_id in alive)
    assert ghost_pair_slots == ["g2"]
    assert all(not pair <= {"g1", "g2"} for pair in pairs_from_match(match))


def test_pairing_with_two_alive_and_four_ghosts_pairs_alive_players():
    players = [
        make_player("a"),
        make_player("b"),
        make_player("g1", ghost=True, eliminated_round=1),
        make_player("g2", ghost=True, eliminated_round=2),
        make_player("g3", ghost=True, eliminated_round=3),
        make_player("g4", ghost=True, eliminated_round=4),
    ]
    match = Match(match_id="ghost-pairing", players=players, seed=42)

    match._compute_combat_pairs()

    assert pairs_from_match(match) == {frozenset(("a", "b"))}


def test_ghost_does_not_take_damage_after_losing_combat():
    alive = make_player("alive")
    alive.board = [bare(5, 5, tier=1)]
    ghost = make_player("ghost", ghost=True, eliminated_round=1)
    match = Match(match_id="ghost-combat", players=[alive, ghost], seed=42)
    match._combat_pairs = {"alive": "ghost", "ghost": "alive"}

    with patch("asyncio.sleep", new_callable=AsyncMock):
        asyncio.run(CombatPhase().wait(match))

    assert ghost.health == 0
    assert alive.health == 40


def test_ghost_board_is_frozen_at_elimination_round():
    alive = make_player("alive")
    alive.board = [bare(5, 5, tier=1)]
    ghost = make_player("ghost", ghost=True, eliminated_round=1)
    frozen_board = [minion.copy() for minion in ghost.last_combat_board]
    ghost.board = [bare(100, 100, tier=6)]
    match = Match(match_id="ghost-freeze", players=[alive, ghost], seed=42)
    match._combat_pairs = {"alive": "ghost", "ghost": "alive"}

    with patch("asyncio.sleep", new_callable=AsyncMock):
        asyncio.run(CombatPhase().wait(match))
    match.round = 2
    alive.health = 40
    match._combat_pairs = {"alive": "ghost", "ghost": "alive"}
    with patch("asyncio.sleep", new_callable=AsyncMock):
        asyncio.run(CombatPhase().wait(match))

    assert ghost.last_combat_board == frozen_board
    assert alive.health == 40
