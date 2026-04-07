from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any, List, Optional

from ...combat import resolve_combat
from .base import Phase

if TYPE_CHECKING:
    from ..match import Match

logger = logging.getLogger(__name__)
Message = dict[str, Any]

DISPLAY_DELAY = 6.0  # seconds after broadcasting results, for client animation


class CombatPhase(Phase):
    """
    Combat (fight) phase.

    There is no countdown timer during combat — the fight resolves
    deterministically and instantly.  Once results are broadcast, a fixed
    display delay lets the client animate the battle before control returns
    to the game loop, which then starts the next buy phase timer.

    Timeline:
        1. resolve_combat()        — synchronous, no time limit
        2. broadcast combat_log    — full event list for client replay
        3. apply damage            — mutate player health
        4. broadcast combat_result — summary + new health totals
        5. check win condition
        6. sleep DISPLAY_DELAY     — client animates; buy timer has NOT started yet
        → caller starts BuyPhase.enter(), which sets buy_phase_started_at
    """

    name = "combat"
    duration = None  # no countdown; ends when fight resolves + display delay elapses

    async def enter(self, match: Match) -> None:
        match.phase = "combat"
        match._buy_phase_started_at = None
        await match.broadcast({"type": "combat_start", "round": match.round})

    async def wait(self, match: Match) -> None:
        pid0, pid1 = match.player_order
        p0 = match.players[pid0]
        p1 = match.players[pid1]

        # 1. Resolve combat — deterministic, no time limit
        result = resolve_combat(
            board_a=p0.board,
            board_b=p1.board,
            rng=match.rng,
            tavern_tier_a=p0.tavern_tier,
            tavern_tier_b=p1.tavern_tier,
        )

        # 2. Broadcast full event log so the client can replay the fight
        await match.broadcast(
            {
                "type": "combat_log",
                "round": match.round,
                "players": [pid0, pid1],
                "initial_a": [m.to_dict() for m in p0.board],
                "initial_b": [m.to_dict() for m in p1.board],
                "events": result["events"],
                "surviving_a": result["surviving_a"],
                "surviving_b": result["surviving_b"],
            }
        )

        # 3. Apply damage
        winner_idx: Optional[int] = result["winner"]
        damage: int = result["damage"]
        if winner_idx == 0:
            p1.health -= damage
        elif winner_idx == 1:
            p0.health -= damage

        # 4. Broadcast result summary
        await match.broadcast(
            {
                "type": "combat_result",
                "round": match.round,
                "winner_player": None if winner_idx is None else match.player_order[winner_idx],
                "damage": damage,
                "health": {pid0: p0.health, pid1: p1.health},
            }
        )

        # 5. Check win condition
        alive: List[str] = [pid for pid, p in match.players.items() if p.health > 0]
        if len(alive) < 2:
            match.winner = alive[0] if alive else max(
                match.players, key=lambda pid: match.players[pid].health
            )
            match.phase = "game_over"

        # 6. Display delay — the next buy phase timer will NOT start until
        #    this sleep returns and BuyPhase.enter() is called by the game loop.
        await asyncio.sleep(DISPLAY_DELAY)
