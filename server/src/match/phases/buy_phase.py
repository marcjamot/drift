from __future__ import annotations

import asyncio
import time
from collections import Counter
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
            ctx = BuyContext(player=player, rng=match.rng)
            event = RoundStartEvent(round=match.round, owner=player)
            ctx.trigger("on_round_start", event)
            ctx.trigger_hero("on_round_start", event)

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
        if kind == "discover_pick":
            return self._act_discover_pick(player, action, match)
        if kind == "use_hero_power":
            return self._act_use_hero_power(player, action, match)
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

        ctx = BuyContext(player=player, rng=match.rng)
        event = BuyEvent(subject=minion, owner=player, shop_index=idx)
        ctx.trigger("on_buy", event)
        ctx.trigger_hero("on_buy", event)
        self._check_triple(player, match)
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
        play_event = PlayEvent(subject=minion, owner=player, hand_index=idx, source="hand")
        spawn_event = SpawnEvent(subject=minion, source="play", owner=player)
        ctx.trigger("on_play", play_event)
        ctx.trigger_hero("on_play", play_event)
        ctx.trigger("on_spawn", spawn_event)
        ctx.trigger_hero("on_spawn", spawn_event)
        self._check_triple(player, match)
        return {"ok": True}

    def _act_sell(self, player: PlayerState, action: Message, match: Match) -> ActionResult:
        idx = action.get("board_index")
        if idx is None or not (0 <= idx < len(player.board)):
            return {"error": "invalid board_index"}

        minion = player.board[idx]
        ctx = BuyContext(player=player, rng=match.rng)
        sell_event = SellEvent(subject=minion, owner=player, board_index=idx)
        ctx.trigger("on_sell", sell_event)
        ctx.trigger_hero("on_sell", sell_event)
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
        if player.pending_discover:
            return {"error": "resolve your discover first"}
        player.locked = True
        if all(p.locked for p in match.players.values()):
            match._phase_end.set()
        return {"ok": True}

    def _act_discover_pick(self, player: PlayerState, action: Message, match: Match) -> ActionResult:
        if not player.pending_discover:
            return {"error": "no pending discover"}
        idx = action.get("index")
        if idx is None or not (0 <= idx < len(player.pending_discover)):
            return {"error": "invalid discover index"}
        options = player.pending_discover
        chosen = options.pop(idx)
        match.pool.return_cards(options)
        player.pending_discover = None
        player.hand.append(chosen)
        self._check_triple(player, match)
        return {"ok": True}

    def _act_use_hero_power(self, player: PlayerState, action: Message, match: Match) -> ActionResult:
        from ...heroes.base import HeroPowerEvent
        hero = player.hero
        if not hero or hero.hero_power_type == "passive" or not hero.hero_power:
            return {"error": "no active hero power"}
        if player.hero_power_uses_left <= 0:
            return {"error": "hero power already used this round"}

        target = None
        target_zone = ""
        target_index = -1

        if hero.hero_power_type.startswith("active_target_"):
            zone = action.get("target_zone")
            idx = action.get("target_index")
            if zone is None or idx is None:
                return {"error": "target_zone and target_index required"}
            expected = hero.hero_power_type.removeprefix("active_target_")
            if zone != expected:
                return {"error": f"must target a card in {expected}"}
            idx = int(idx)
            if zone == "shop":
                if not (0 <= idx < len(player.shop)) or player.shop[idx] is None:
                    return {"error": "invalid shop target"}
                target = player.shop[idx]
            elif zone == "hand":
                if not (0 <= idx < len(player.hand)):
                    return {"error": "invalid hand target"}
                target = player.hand[idx]
            target_zone = zone
            target_index = idx

        player.hero_power_uses_left -= 1
        ctx = BuyContext(player=player, rng=match.rng)
        hero.hero_power(HeroPowerEvent(owner=player, target=target, target_zone=target_zone, target_index=target_index), ctx)
        return {"ok": True}

    # ── triple / discover helpers ─────────────────────────────────────────────

    def _check_triple(self, player: PlayerState, match: Match) -> None:
        """Check if any card_id appears 3+ times across hand+board and resolve."""
        all_cards = [m.card_id for m in player.hand] + [m.card_id for m in player.board]
        counts = Counter(all_cards)
        for card_id, count in counts.items():
            if count >= 3:
                self._resolve_triple(player, match, card_id)
                return

    def _resolve_triple(self, player: PlayerState, match: Match, card_id: str) -> None:
        from ...cards.catalog import CARD_CATALOG

        # Remove 3 copies — hand first, then board
        removed = 0
        for collection in [player.hand, player.board]:
            i = 0
            while i < len(collection) and removed < 3:
                if collection[i].card_id == card_id:
                    collection.pop(i)
                    removed += 1
                else:
                    i += 1

        # Create golden and place in hand
        card_def = CARD_CATALOG[card_id]
        golden = card_def.create_golden_instance()
        player.hand.append(golden)

        # Offer discover from tier+1 (capped at 6)
        discover_tier = min(player.tavern_tier + 1, 6)
        options = match.pool.draw_at_tier(3, discover_tier)
        # Fall back to any available tier if not enough at that tier
        if len(options) < 3:
            options.extend(match.pool.draw(3 - len(options), discover_tier))
        player.pending_discover = options
