from __future__ import annotations

import asyncio
from typing import Any, Callable

from ..engine.bot import choose_shop_actions
from ..engine.context import MatchContext, ShopStateContext
from ..engine.models import BOARD_SIZE, BUY_COST, REFRESH_COST, SELL_VALUE, SHOP_SIZE_BY_TIER, Minion
from ..engine.state_machine import State

ActionHandler = Callable[[Any, dict[str, Any], MatchContext], dict[str, Any]]
BUY_DEADLINE = 60.0


class ShopState(State):
    name = "shop"
    type = "shop"
    deadline_seconds = BUY_DEADLINE
    duration = BUY_DEADLINE

    def __init__(self) -> None:
        self._actions: dict[str, ActionHandler] = {}

    def register_action(self, name: str, handler: ActionHandler) -> None:
        self._actions[name] = handler

    async def enter(self, ctx: MatchContext) -> None:
        if ctx.phase not in {"waiting", "hero_select", "begin"}:
            ctx.round += 1
        ctx.phase = self.type
        ctx.enter_state(ShopStateContext(match=ctx))
        ctx.phase_end.clear()

        for player in ctx.players.values():
            player.start_round(ctx.round)
            if player.frozen:
                ctx.emit("shop.freeze", {"player_id": player.player_id, "value": False})
                player.frozen = False
            else:
                self.refresh_shop(ctx, player)
            ctx.event_bus.emit({"event": "round_start", "round": ctx.round, "owner": player})

        ctx.replay.update_current_snapshot(ctx)

        for player in ctx.players.values():
            if player.is_bot and player.health > 0:
                for action in choose_shop_actions(player):
                    await self.handle_action(player.player_id, action, ctx)

        await ctx.broadcast_state()
        try:
            await asyncio.wait_for(ctx.phase_end.wait(), timeout=self.deadline_seconds)
        except asyncio.TimeoutError:
            pass

    def refresh_shop(self, ctx: MatchContext, player: Any) -> None:
        ctx.pool.return_minions([minion for minion in player.shop if minion is not None])
        size = SHOP_SIZE_BY_TIER.get(player.tavern_tier, 3)
        new_shop = ctx.pool.draw(size, player.tavern_tier)
        player.shop = new_shop
        for minion in [m for m in player.shop if m]:
            minion.bind(ctx.store)
            card = ctx.catalog.maybe_get(minion.card_id)
            if card and ctx.state_context:
                card.on_state(minion, ctx.state_context)
        ctx.emit("shop.refresh", {
            "player_id": player.player_id,
            "shop": [m.to_dict() if m else None for m in player.shop],
        })

    async def handle_action(self, player_id: str, action: dict[str, Any], ctx: MatchContext) -> dict[str, Any]:
        player = ctx.players.get(player_id)
        if not player:
            return {"error": "unknown player"}
        if player.locked:
            return {"error": "already locked - cannot act"}

        kind = action.get("type")
        if kind == "buy":
            result = self._buy(ctx, player, action.get("shop_index"))
        elif kind == "play":
            result = self._play(ctx, player, action.get("hand_index"))
        elif kind == "sell":
            result = self._sell(ctx, player, action.get("board_index"))
        elif kind == "reorder":
            result = self._reorder(ctx, player, action.get("from_index"), action.get("to_index"))
        elif kind == "freeze":
            player.frozen = not player.frozen
            ctx.emit("shop.freeze", {"player_id": player.player_id, "value": player.frozen},
                     {f"player:{player.player_id}:frozen": player.frozen})
            result = {"ok": True}
        elif kind == "refresh":
            result = self._refresh(ctx, player)
        elif kind == "upgrade":
            result = self._upgrade(ctx, player)
        elif kind == "lock":
            player.locked = True
            ctx.emit("shop.lock", {
                "player_id": player.player_id,
                "player_after": player.to_dict(as_self=True),
            }, {f"player:{player.player_id}:locked": True})
            result = {"ok": True}
            alive_humans = [p for p in ctx.players.values() if not p.is_bot and p.health > 0]
            if all(p.locked for p in alive_humans):
                ctx.phase_end.set()
        elif kind in {"hero_power", "use_hero_power"}:
            result = self._hero_power(ctx, player, action)
        elif kind == "discover_pick":
            result = self._discover_pick(ctx, player, action.get("index"))
        elif kind in self._actions:
            result = self._actions[kind](player, action, ctx)
        else:
            return {"error": f"unknown action: {kind!r}"}

        if result.get("ok"):
            self._check_triple(ctx, player)
        return result

    def _buy(self, ctx: MatchContext, player: Any, shop_index: Any) -> dict[str, Any]:
        if shop_index is None or not (0 <= shop_index < len(player.shop)):
            return {"error": "invalid shop_index"}
        minion = player.shop[shop_index]
        if minion is None:
            return {"error": "empty shop slot"}
        if player.gold < BUY_COST:
            return {"error": "not enough gold"}
        player.shop[shop_index] = None
        player.hand.append(minion)
        new_gold = player.gold - BUY_COST
        player.gold = new_gold
        ctx.emit("shop.buy", {
            "player_id": player.player_id,
            "shop_index": shop_index,
            "minion_id": minion.instance_id,
            "gold": new_gold,
        }, {f"player:{player.player_id}:gold": new_gold}, visible_to=[player.player_id])
        ctx.event_bus.emit({"event": "buy", "owner": player, "subject": minion, "shop_index": shop_index})
        return {"ok": True}

    def _play(self, ctx: MatchContext, player: Any, hand_index: Any) -> dict[str, Any]:
        if hand_index is None or not (0 <= hand_index < len(player.hand)):
            return {"error": "invalid hand_index"}
        if len(player.board) >= BOARD_SIZE:
            return {"error": "board is full"}
        minion = player.hand.pop(hand_index)
        position = len(player.board)
        player.board.append(minion)
        ctx.emit("entity.spawn", {
            "owner_id": player.player_id,
            "position": position,
            "minion_id": minion.instance_id,
            "minion": minion.to_dict(),
        })
        ctx.event_bus.emit({"event": "play", "owner": player, "subject": minion, "hand_index": hand_index})
        ctx.event_bus.emit({"event": "spawn", "owner": player, "subject": minion, "source": "play"})
        return {"ok": True}

    def _sell(self, ctx: MatchContext, player: Any, board_index: Any) -> dict[str, Any]:
        if board_index is None or not (0 <= board_index < len(player.board)):
            return {"error": "invalid board_index"}
        minion = player.board.pop(board_index)
        new_gold = min(player.gold + SELL_VALUE, player.max_gold)
        player.gold = new_gold
        ctx.emit("shop.sell", {
            "player_id": player.player_id,
            "minion_id": minion.instance_id,
            "gold": new_gold,
        }, {f"player:{player.player_id}:gold": new_gold})
        card_def = ctx.catalog.maybe_get(minion.card_id)
        if card_def:
            ctx.pool.return_card(card_def)
        ctx.event_bus.emit({"event": "sell", "owner": player, "subject": minion, "board_index": board_index})
        return {"ok": True}

    def _reorder(self, ctx: MatchContext, player: Any, from_index: Any, to_index: Any) -> dict[str, Any]:
        if from_index is None or to_index is None:
            return {"error": "from_index and to_index required"}
        if not (0 <= from_index < len(player.board)):
            return {"error": "invalid from_index"}
        to_index = max(0, min(int(to_index), BOARD_SIZE - 1))
        actual_to = min(to_index, len(player.board))
        minion = player.board.pop(from_index)
        player.board.insert(actual_to, minion)
        ctx.emit("entity.move", {
            "player_id": player.player_id,
            "minion_id": minion.instance_id,
            "from_index": from_index,
            "to_index": actual_to,
        })
        return {"ok": True}

    def _refresh(self, ctx: MatchContext, player: Any) -> dict[str, Any]:
        if player.gold < REFRESH_COST:
            return {"error": "not enough gold"}
        new_gold = player.gold - REFRESH_COST
        player.gold = new_gold
        ctx.emit("shop.gold", {"player_id": player.player_id, "gold": new_gold},
                 {f"player:{player.player_id}:gold": new_gold})
        self.refresh_shop(ctx, player)
        return {"ok": True}

    def _upgrade(self, ctx: MatchContext, player: Any) -> dict[str, Any]:
        if player.tavern_tier >= 6:
            return {"error": "already max tavern tier"}
        if player.gold < player.upgrade_cost:
            return {"error": "not enough gold"}
        new_gold = player.gold - player.upgrade_cost
        player.gold = new_gold
        player.tavern_tier += 1
        player.upgrade_cost = max(0, {1: 5, 2: 7, 3: 8, 4: 9, 5: 10}.get(player.tavern_tier, 999) - (ctx.round - 1))
        ctx.emit("shop.upgrade", {
            "player_id": player.player_id,
            "tavern_tier": player.tavern_tier,
            "gold": new_gold,
        }, {
            f"player:{player.player_id}:gold": new_gold,
            f"player:{player.player_id}:tavern_tier": player.tavern_tier,
        })
        return {"ok": True}

    def _hero_power(self, ctx: MatchContext, player: Any, action: dict[str, Any]) -> dict[str, Any]:
        if not player.hero or player.hero.hero_power_type == "passive":
            return {"error": "no active hero power"}
        if player.hero_power_uses_left <= 0:
            return {"error": "hero power already used this round"}
        player.hero_power_uses_left -= 1
        ctx.emit("hero_power.use", {
            "player_id": player.player_id,
            "hero_id": player.hero.id,
            "action": action,
        }, {f"player:{player.player_id}:hero_power_uses_left": player.hero_power_uses_left})
        ctx.event_bus.emit({"event": "hero_power", "owner": player, "action": action})
        return {"ok": True}

    def _discover_pick(self, ctx: MatchContext, player: Any, index: Any) -> dict[str, Any]:
        if player.pending_discover is None:
            return {"error": "no pending discover"}
        if index is None or not (0 <= index < len(player.pending_discover)):
            return {"error": "invalid discover index"}
        picked = player.pending_discover[index]
        player.hand.append(picked)
        player.pending_discover = None
        ctx.emit("shop.discover_pick", {
            "player_id": player.player_id,
            "index": index,
            "minion_id": picked.instance_id,
        })
        return {"ok": True}

    def _check_triple(self, ctx: MatchContext, player: Any) -> None:
        zones: list[tuple[str, Minion]] = [("hand", m) for m in player.hand] + [("board", m) for m in player.board]
        by_card: dict[str, list[tuple[str, Minion]]] = {}
        for zone, minion in zones:
            if not minion.golden:
                by_card.setdefault(minion.card_id, []).append((zone, minion))
        for card_id, copies in by_card.items():
            if len(copies) < 3:
                continue
            removed = 0
            for zone, minion in copies[:3]:
                target = player.hand if zone == "hand" else player.board
                if minion in target:
                    target.remove(minion)
                    removed += 1
            if removed == 3:
                golden = ctx.catalog.get(card_id).create_golden_instance()
                golden.bind(ctx.store)
                if ctx.state_context:
                    ctx.catalog.get(card_id).on_state(golden, ctx.state_context)
                player.hand.append(golden)
                discover_tier = min(golden.tier + 1, 6)
                player.pending_discover = ctx.pool.draw_at_tier(3, discover_tier)
                for m in player.pending_discover:
                    m.bind(ctx.store)
                ctx.emit("shop.triple", {
                    "player_id": player.player_id,
                    "golden_id": golden.instance_id,
                    "discover_options": [m.to_dict() for m in player.pending_discover],
                })
                ctx.event_bus.emit({"event": "triple", "owner": player, "subject": golden})
            return
