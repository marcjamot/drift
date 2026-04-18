from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Any

from ...cards.base import RoundStartEvent
from ...player import BuyContext
from .. import actions
from .base import Phase

if TYPE_CHECKING:
    from ..match import Match

Message = dict[str, Any]
ActionResult = dict[str, Any]

DURATION = 60.0  # seconds players have to act each buy round


class BuyPhase(Phase):
    """
    Buy (preparation) phase.

    All game-logic lives in src/match/actions.py (pure functions, testable
    without async infrastructure).  This class owns only the async lifecycle
    and the I/O — broadcasting state and gating on the timer / lock event.
    """

    name = "buy"
    duration = DURATION

    # ── phase lifecycle ───────────────────────────────────────────────────────

    async def enter(self, match: Match) -> None:
        from ..bot import run_bot_buy_phase

        if match.phase != "waiting":
            match.round += 1
        match.phase = "buy"
        match._phase_end.clear()
        match._buy_phase_started_at = time.monotonic()

        for player in match.players.values():
            player.start_round(match.round)
            if player.frozen:
                player.frozen = False
            else:
                actions.refresh_shop(player, match.pool)
            ctx = BuyContext(player=player, rng=match.rng)
            event = RoundStartEvent(round=match.round, owner=player)
            ctx.trigger("on_round_start", event)
            ctx.trigger_hero("on_round_start", event)

        for player in match.players.values():
            if player.is_bot and player.health > 0:
                run_bot_buy_phase(player, match)

        await match._broadcast_state()

    async def wait(self, match: Match) -> None:
        try:
            await asyncio.wait_for(match._phase_end.wait(), timeout=self.duration)
        except asyncio.TimeoutError:
            pass

    # ── action dispatch ───────────────────────────────────────────────────────

    async def handle_action(
        self, player_id: str, action: Message, match: Match
    ) -> ActionResult:
        player = match.players.get(player_id)
        if not player:
            return {"error": "unknown player"}
        if player.locked:
            return {"error": "already locked — cannot act"}

        kind = action.get("type")

        result: ActionResult

        if kind == "buy":
            result = actions.buy(player, action.get("shop_index"), match.pool, match.rng)
        elif kind == "play":
            result = actions.play(player, action.get("hand_index"), match.pool, match.rng)
        elif kind == "sell":
            result = actions.sell(player, action.get("board_index"), match.pool, match.rng)
        elif kind == "reorder":
            result = actions.reorder(player, action.get("from_index"), action.get("to_index"))
        elif kind == "freeze":
            result = actions.freeze(player)
        elif kind == "refresh":
            result = actions.refresh(player, match.pool)
        elif kind == "upgrade":
            result = actions.upgrade(player, match.round)
        elif kind == "lock":
            result = actions.lock(player)
            if result.get("ok"):
                alive_humans = [
                    p for p in match.players.values()
                    if not p.is_bot and p.health > 0
                ]
                if all(p.locked for p in alive_humans):
                    match._phase_end.set()
        elif kind == "discover_pick":
            result = actions.discover_pick(
                player, action.get("index"), match.pool, match.rng
            )
        elif kind == "use_hero_power":
            result = actions.use_hero_power(player, action, match.rng)
        else:
            return {"error": f"unknown action: {kind!r}"}

        if result.get("ok") and player.is_bot:
            actions.auto_pick_discovers(player, match.pool, match.rng)

        return result
