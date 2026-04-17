from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Tuple

from ...combat import resolve_combat
from .base import Phase

if TYPE_CHECKING:
    from ..match import Match

logger = logging.getLogger(__name__)
Message = dict[str, Any]

DISPLAY_DELAY = 6.0  # seconds after broadcasting results, for client animation


class CombatPhase(Phase):
    """
    Combat phase — resolves all random 1v1 pairings simultaneously.

    Timeline per pair:
        1. Capture initial boards (before resolve_combat modifies copies)
        2. resolve_combat()        — synchronous, deterministic
        3. Apply damage to loser
        4. Send combat_log to human players in each pair
    After all pairs:
        5. Assign placements for newly dead players
        6. Check win condition
        7. Send combat_result to each human
        8. Broadcast updated state
        9. Notify eliminations  — sends game_over to dead humans
       10. sleep DISPLAY_DELAY (only if human is still alive / had a combat)
    """

    name = "combat"
    duration = None

    async def enter(self, match: Match) -> None:
        match.phase = "combat"
        match._buy_phase_started_at = None
        await match._broadcast_combat_start()

    async def wait(self, match: Match) -> None:
        pairs_done: Set[str] = set()

        # Collect results per player_id for combat_result messages
        pair_results: Dict[str, dict] = {}

        for pid_a, pid_b in match._combat_pairs.items():
            if pid_a in pairs_done:
                continue
            pairs_done.add(pid_a)
            pairs_done.add(pid_b)

            p_a = match.players[pid_a]
            p_b = match.players[pid_b]

            # 1. Snapshot boards before combat (resolve_combat takes deep copies)
            initial_a = [m.to_dict() for m in p_a.board]
            initial_b = [m.to_dict() for m in p_b.board]

            # Save last_combat_board for leaderboard display
            p_a.last_combat_board = initial_a
            p_b.last_combat_board = initial_b

            # 2. Resolve combat
            result = resolve_combat(
                board_a=p_a.board,
                board_b=p_b.board,
                rng=match.rng,
                tavern_tier_a=p_a.tavern_tier,
                tavern_tier_b=p_b.tavern_tier,
                hero_a=p_a.hero,
                hero_b=p_b.hero,
            )

            # 3. Apply damage
            winner_idx: Optional[int] = result["winner"]
            damage: int = result["damage"]
            if winner_idx == 0:
                match.apply_player_damage(p_b, damage)
            elif winner_idx == 1:
                match.apply_player_damage(p_a, damage)

            # 4. Send combat_log to any human in this pair
            for human_pid in [pid_a, pid_b]:
                if match.players[human_pid].is_bot:
                    continue
                await match._send_combat_log(
                    human_pid,
                    pid_a,
                    pid_b,
                    initial_a,
                    initial_b,
                    result,
                )

            # Store result for combat_result message
            winner_pid: Optional[str] = (
                None if winner_idx is None
                else [pid_a, pid_b][winner_idx]
            )
            combat_result_payload = {
                "winner_player": winner_pid,
                "damage": damage,
                "health": {pid_a: p_a.health, pid_b: p_b.health},
            }
            pair_results[pid_a] = combat_result_payload
            pair_results[pid_b] = combat_result_payload

        # 5. Assign placements for newly dead players
        newly_dead: List[str] = [
            pid for pid in match.player_order
            if match.players[pid].health <= 0
            and match.players[pid].eliminated_round is None
        ]
        if newly_dead:
            match.assign_placements_for_dead(newly_dead)

        # 6. Check win condition
        alive: List[str] = match._alive_players()
        if len(alive) <= 1:
            match.winner = alive[0] if alive else None
            if match.winner:
                match.players[match.winner].placement = 1
            match.phase = "game_over"

        # 7. Send combat_result to each human
        for pid in match._human_players():
            if pid in pair_results:
                await match._send_combat_result(pid, pair_results[pid])

        # 8. Broadcast updated state (includes new HPs and leaderboard)
        await match._broadcast_state()

        # 9. Send game_over to humans who just died
        await match._notify_eliminations()

        # 10. Display delay — buy timer must not start until this returns
        await asyncio.sleep(DISPLAY_DELAY)
