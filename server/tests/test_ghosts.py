import asyncio
from unittest.mock import AsyncMock, patch

from src.match.match import Match
from src.match.phases.combat_phase import CombatPhase
from src.player.player import PlayerState
from .conftest import bare


def _ghost(player_id: str, eliminated_round: int) -> PlayerState:
    p = PlayerState(player_id=player_id, name=player_id, is_bot=True)
    p.health = 0
    p.ghost = True
    p.eliminated_round = eliminated_round
    p.last_combat_board = [
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
    return p


def _alive(player_id: str) -> PlayerState:
    return PlayerState(player_id=player_id, name=player_id, is_bot=True)


def test_ghost_does_not_take_damage_after_losing_combat():
    alive = _alive("alive")
    alive.board = [bare(5, 5, tier=1)]
    ghost = _ghost("ghost", eliminated_round=1)
    match = Match(match_id="ghost-combat", players=[alive, ghost], seed=42)
    match._combat_pairs = {"alive": "ghost", "ghost": "alive"}

    with patch("asyncio.sleep", new_callable=AsyncMock):
        asyncio.run(CombatPhase().wait(match))

    assert ghost.health == 0
    assert alive.health == 40


def test_ghost_board_is_frozen_at_elimination_round():
    alive = _alive("alive")
    alive.board = [bare(5, 5, tier=1)]
    ghost = _ghost("ghost", eliminated_round=1)
    frozen_board = list(ghost.last_combat_board)
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
