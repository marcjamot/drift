from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Any

from ...cards.base import BuyEvent, PlayEvent, RoundStartEvent, SellEvent, SpawnEvent
from ...cards.pool import SHOP_SIZE_BY_TIER
from ...player import (
    BOARD_SIZE,
    BUY_COST,
    BuyContext,
    PlayerState,
    REFRESH_COST,
    SELL_VALUE,
    compute_upgrade_cost,
)
from .base import Phase

if TYPE_CHECKING:
    from ..match import Match

Message = dict[str, Any]
ActionResult = dict[str, Any]

DURATION = 60.0  # seconds players have to act each buy round


class BuyPhase(Phase):
    """
    Buy (preparation) phase.

    Players spend gold to buy, play, sell, reorder, freeze, refresh, or
    upgrade their tavern.  The phase ends when all players lock in or the
    60-second timer expires — whichever comes first.

    The buy timer only starts after enter() is called, which in turn is
    only called once CombatPhase.wait() has fully completed.
    """

    name = "buy"
    duration = DURATION

    # ── phase lifecycle ───────────────────────────────────────────────────────

    async def enter(self, match: Match) -> None:
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
                self._refresh_shop(player, match)
            BuyContext(player=player, rng=match.rng).trigger(
                "on_round_start",
                RoundStartEvent(round=match.round, owner=player),
            )

        await match.broadcast_state()

    async def wait(self, match: Match) -> None:
        try:
            await asyncio.wait_for(match._phase_end.wait(), timeout=self.duration)
        except asyncio.TimeoutError:
            pass

    # ── action dispatch ───────────────────────────────────────────────────────

    async def handle_action(
        self, player_id: str, action: Message, match: Match
    ) -> ActionResult:
        player: PlayerState | None = match.players.get(player_id)
        if not player:
            return {"error": "unknown player"}
        if player.locked:
            return {"error": "already locked — cannot act"}

        kind = action.get("type")
        if kind == "buy":
            return self._act_buy(player, action, match)
        if kind == "play":
            return self._act_play(player, action, match)
        if kind == "sell":
            return self._act_sell(player, action, match)
        if kind == "reorder":
            return self._act_reorder(player, action)
        if kind == "freeze":
            return self._act_freeze(player)
        if kind == "refresh":
            return self._act_refresh(player, match)
        if kind == "upgrade":
            return self._act_upgrade(player, match)
        if kind == "lock":
            return self._act_lock(player, match)
        return {"error": f"unknown action: {kind!r}"}

    # ── shop helper ───────────────────────────────────────────────────────────

    def _refresh_shop(self, player: PlayerState, match: Match) -> None:
        match.pool.return_cards([m for m in player.shop if m is not None])
        size = SHOP_SIZE_BY_TIER.get(player.tavern_tier, 3)
        player.shop = match.pool.draw(size, player.tavern_tier)

    # ── action handlers ───────────────────────────────────────────────────────

    def _act_buy(self, player: PlayerState, action: Message, match: Match) -> ActionResult:
        idx = action.get("shop_index")
        if idx is None or not (0 <= idx < len(player.shop)):
            return {"error": "invalid shop_index"}
        minion = player.shop[idx]
        if minion is None:
            return {"error": "empty shop slot"}
        if player.gold < BUY_COST:
            return {"error": "not enough gold"}

        player.gold -= BUY_COST
        player.shop[idx] = None
        player.hand.append(minion)

        BuyContext(player=player, rng=match.rng).trigger(
            "on_buy", BuyEvent(subject=minion, owner=player, shop_index=idx)
        )
        return {"ok": True}

    def _act_play(self, player: PlayerState, action: Message, match: Match) -> ActionResult:
        idx = action.get("hand_index")
        if idx is None or not (0 <= idx < len(player.hand)):
            return {"error": "invalid hand_index"}
        if len(player.board) >= BOARD_SIZE:
            return {"error": "board is full"}

        minion = player.hand.pop(idx)
        player.board.append(minion)

        ctx = BuyContext(player=player, rng=match.rng)
        ctx.trigger("on_play", PlayEvent(subject=minion, owner=player, hand_index=idx, source="hand"))
        ctx.trigger("on_spawn", SpawnEvent(subject=minion, source="play", owner=player))
        return {"ok": True}

    def _act_sell(self, player: PlayerState, action: Message, match: Match) -> ActionResult:
        idx = action.get("board_index")
        if idx is None or not (0 <= idx < len(player.board)):
            return {"error": "invalid board_index"}

        minion = player.board[idx]
        BuyContext(player=player, rng=match.rng).trigger(
            "on_sell", SellEvent(subject=minion, owner=player, board_index=idx)
        )
        player.board.pop(idx)
        player.gold = min(player.gold + SELL_VALUE, player.max_gold)
        match.pool.return_cards([minion])
        return {"ok": True}

    def _act_reorder(self, player: PlayerState, action: Message) -> ActionResult:
        from_idx = action.get("from_index")
        to_idx = action.get("to_index")
        if from_idx is None or to_idx is None:
            return {"error": "from_index and to_index required"}
        if not (0 <= from_idx < len(player.board)):
            return {"error": "invalid from_index"}
        to_idx = max(0, min(to_idx, BOARD_SIZE - 1))

        minion = player.board.pop(from_idx)
        player.board.insert(min(to_idx, len(player.board)), minion)
        return {"ok": True}

    def _act_freeze(self, player: PlayerState) -> ActionResult:
        player.frozen = not player.frozen
        return {"ok": True}

    def _act_refresh(self, player: PlayerState, match: Match) -> ActionResult:
        if player.gold < REFRESH_COST:
            return {"error": "not enough gold"}
        player.gold -= REFRESH_COST
        self._refresh_shop(player, match)
        return {"ok": True}

    def _act_upgrade(self, player: PlayerState, match: Match) -> ActionResult:
        if player.tavern_tier >= 6:
            return {"error": "already max tavern tier"}
        if player.gold < player.upgrade_cost:
            return {"error": "not enough gold"}
        player.gold -= player.upgrade_cost
        player.tavern_tier += 1
        player.upgrade_cost = compute_upgrade_cost(player.tavern_tier, match.round)
        return {"ok": True}

    def _act_lock(self, player: PlayerState, match: Match) -> ActionResult:
        player.locked = True
        if all(p.locked for p in match.players.values()):
            match._phase_end.set()
        return {"ok": True}
