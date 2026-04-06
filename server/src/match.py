import asyncio
import json
import logging
import math
import random
import time
from typing import Any, Awaitable, Callable, Dict, List, Optional

from .cards.base import BuyEvent, PlayEvent, RoundStartEvent, SellEvent, SpawnEvent
from .cards.catalog import CARD_CATALOG
from .cards.pool import CardPool, SHOP_SIZE_BY_TIER
from .combat import resolve_combat
from .player import (
    BUY_COST,
    BOARD_SIZE,
    REFRESH_COST,
    SELL_VALUE,
    BuyContext,
    PlayerState,
    compute_upgrade_cost,
)

logger = logging.getLogger(__name__)

BUY_TIMER = 60
COMBAT_RESULT_DELAY_SECONDS = 6.0
Message = dict[str, Any]
ActionResult = dict[str, Any]
Sender = Callable[[str], Awaitable[None]]


class Match:
    def __init__(
        self,
        match_id: str,
        players: List[PlayerState],
        seed: Optional[int] = None,
    ) -> None:
        self.match_id = match_id
        self.player_order: List[str] = [p.player_id for p in players]
        self.players: Dict[str, PlayerState] = {p.player_id: p for p in players}

        self.seed: int = seed if seed is not None else hash(match_id) & 0xFFFFFFFF
        self.rng = random.Random(self.seed)

        self.round: int = 1
        self.phase: str = "waiting"
        self.winner: Optional[str] = None

        self.pool: CardPool = CardPool(list(CARD_CATALOG.values()), random.Random(self.seed ^ 0xDEAD))

        self._senders: Dict[str, Sender] = {}
        self._lock = asyncio.Lock()
        self._phase_end = asyncio.Event()
        self._buy_phase_started_at: Optional[float] = None

    def register_sender(self, player_id: str, send_fn: Sender) -> None:
        self._senders[player_id] = send_fn

    def unregister_sender(self, player_id: str) -> None:
        self._senders.pop(player_id, None)

    async def send_to(self, player_id: str, msg: Message) -> None:
        fn: Optional[Sender] = self._senders.get(player_id)
        if fn:
            try:
                await fn(json.dumps(msg))
            except Exception as exc:
                logger.warning("Send to %s failed: %s", player_id, exc)

    async def broadcast(self, msg: Message) -> None:
        for pid in self.player_order:
            await self.send_to(pid, msg)

    async def send_state(self, player_id: str) -> None:
        player: PlayerState = self.players[player_id]
        opp_id: str = self._opponent(player_id)
        opp: PlayerState = self.players[opp_id]
        buy_seconds_left: int | None = None
        if self.phase == "buy" and self._buy_phase_started_at is not None:
            buy_seconds_left = max(
                0, math.ceil(BUY_TIMER - (time.monotonic() - self._buy_phase_started_at))
            )
        await self.send_to(
            player_id,
            {
                "type": "state",
                "round": self.round,
                "phase": self.phase,
                "winner": self.winner,
                "buy_seconds_left": buy_seconds_left,
                "self": player.to_dict(as_self=True),
                "opponent": opp.to_dict(as_self=False),
            },
        )

    async def broadcast_state(self) -> None:
        for pid in self.player_order:
            await self.send_state(pid)

    async def run(self) -> None:
        for player in self.players.values():
            self._refresh_shop(player)

        while self.phase != "game_over":
            await self._buy_phase()
            if self.phase == "game_over":
                break
            await self._combat_phase()

        await self.broadcast({"type": "game_over", "winner": self.winner})

    async def _buy_phase(self) -> None:
        if self.phase != "waiting":
            self.round += 1
        self.phase = "buy"
        self._phase_end.clear()
        self._buy_phase_started_at = time.monotonic()

        for player in self.players.values():
            player.start_round(self.round)
            if player.frozen:
                player.frozen = False
            else:
                self._refresh_shop(player)
            BuyContext(player=player, rng=self.rng).trigger(
                "on_round_start",
                RoundStartEvent(round=self.round, owner=player),
            )

        await self.broadcast_state()

        try:
            await asyncio.wait_for(self._phase_end.wait(), timeout=BUY_TIMER)
        except asyncio.TimeoutError:
            pass

    async def _combat_phase(self) -> None:
        self.phase = "combat"
        self._buy_phase_started_at = None
        await self.broadcast({"type": "combat_start", "round": self.round})

        pid0, pid1 = self.player_order
        p0: PlayerState = self.players[pid0]
        p1: PlayerState = self.players[pid1]

        result: dict[str, Any] = resolve_combat(
            board_a=p0.board,
            board_b=p1.board,
            rng=self.rng,
            tavern_tier_a=p0.tavern_tier,
            tavern_tier_b=p1.tavern_tier,
        )

        await self.broadcast(
            {
                "type": "combat_log",
                "round": self.round,
                "players": [pid0, pid1],
                "initial_a": [m.to_dict() for m in p0.board],
                "initial_b": [m.to_dict() for m in p1.board],
                "events": result["events"],
                "surviving_a": result["surviving_a"],
                "surviving_b": result["surviving_b"],
            }
        )

        winner_idx: int | None = result["winner"]
        damage: int = result["damage"]
        if winner_idx == 0:
            p1.health -= damage
        elif winner_idx == 1:
            p0.health -= damage

        await self.broadcast(
            {
                "type": "combat_result",
                "round": self.round,
                "winner_player": None if winner_idx is None else self.player_order[winner_idx],
                "damage": damage,
                "health": {pid0: p0.health, pid1: p1.health},
            }
        )

        alive: List[str] = [pid for pid, p in self.players.items() if p.health > 0]
        if len(alive) < 2:
            if alive:
                self.winner = alive[0]
            else:
                self.winner = max(self.players, key=lambda pid: self.players[pid].health)
            self.phase = "game_over"

        await asyncio.sleep(COMBAT_RESULT_DELAY_SECONDS)

    def _refresh_shop(self, player: PlayerState) -> None:
        self.pool.return_cards([m for m in player.shop if m is not None])
        size: int = SHOP_SIZE_BY_TIER.get(player.tavern_tier, 3)
        player.shop = self.pool.draw(size, player.tavern_tier)

    async def handle_action(self, player_id: str, action: Message) -> ActionResult:
        async with self._lock:
            kind: Any = action.get("type")

            if kind == "concede":
                return self._act_concede(player_id)

            if self.phase != "buy":
                return {"error": "not in buy phase"}

            player: PlayerState | None = self.players.get(player_id)
            if not player:
                return {"error": "unknown player"}
            if player.locked:
                return {"error": "already locked — cannot act"}

            if kind == "buy":
                result: ActionResult = self._act_buy(player, action)
            elif kind == "play":
                result = self._act_play(player, action)
            elif kind == "sell":
                result = self._act_sell(player, action)
            elif kind == "reorder":
                result = self._act_reorder(player, action)
            elif kind == "freeze":
                result = self._act_freeze(player, action)
            elif kind == "refresh":
                result = self._act_refresh(player, action)
            elif kind == "upgrade":
                result = self._act_upgrade(player, action)
            elif kind == "lock":
                result = self._act_lock(player, action)
            else:
                return {"error": f"unknown action: {kind!r}"}

            if result.get("ok"):
                for pid in self.player_order:
                    await self.send_state(pid)
            return result

    def _act_buy(self, player: PlayerState, action: Message) -> ActionResult:
        idx: Any = action.get("shop_index")
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

        ctx: BuyContext = BuyContext(player=player, rng=self.rng)
        ctx.trigger("on_buy", BuyEvent(subject=minion, owner=player, shop_index=idx))

        return {"ok": True}

    def _act_play(self, player: PlayerState, action: Message) -> ActionResult:
        idx: Any = action.get("hand_index")
        if idx is None or not (0 <= idx < len(player.hand)):
            return {"error": "invalid hand_index"}
        if len(player.board) >= BOARD_SIZE:
            return {"error": "board is full"}

        minion = player.hand.pop(idx)
        player.board.append(minion)

        ctx: BuyContext = BuyContext(player=player, rng=self.rng)
        ctx.trigger("on_play", PlayEvent(subject=minion, owner=player, hand_index=idx, source="hand"))
        ctx.trigger("on_spawn", SpawnEvent(subject=minion, source="play", owner=player))

        return {"ok": True}

    def _act_sell(self, player: PlayerState, action: Message) -> ActionResult:
        idx: Any = action.get("board_index")
        if idx is None or not (0 <= idx < len(player.board)):
            return {"error": "invalid board_index"}
        minion = player.board[idx]
        BuyContext(player=player, rng=self.rng).trigger(
            "on_sell",
            SellEvent(subject=minion, owner=player, board_index=idx),
        )

        player.board.pop(idx)
        player.gold = min(player.gold + SELL_VALUE, player.max_gold)
        self.pool.return_cards([minion])

        return {"ok": True}

    def _act_reorder(self, player: PlayerState, action: Message) -> ActionResult:
        from_idx: Any = action.get("from_index")
        to_idx: Any = action.get("to_index")
        if from_idx is None or to_idx is None:
            return {"error": "from_index and to_index required"}
        if not (0 <= from_idx < len(player.board)):
            return {"error": "invalid from_index"}
        to_idx = max(0, min(to_idx, BOARD_SIZE - 1))

        minion = player.board.pop(from_idx)
        insert_at: int = min(to_idx, len(player.board))
        player.board.insert(insert_at, minion)

        return {"ok": True}

    def _act_freeze(self, player: PlayerState, action: Message) -> ActionResult:
        player.frozen = not player.frozen
        return {"ok": True}

    def _act_refresh(self, player: PlayerState, action: Message) -> ActionResult:
        if player.gold < REFRESH_COST:
            return {"error": "not enough gold"}
        player.gold -= REFRESH_COST
        self._refresh_shop(player)
        return {"ok": True}

    def _act_upgrade(self, player: PlayerState, action: Message) -> ActionResult:
        if player.tavern_tier >= 6:
            return {"error": "already max tavern tier"}
        if player.gold < player.upgrade_cost:
            return {"error": "not enough gold"}

        player.gold -= player.upgrade_cost
        player.tavern_tier += 1
        player.upgrade_cost = compute_upgrade_cost(player.tavern_tier, self.round)

        return {"ok": True}

    def _act_concede(self, player_id: str) -> ActionResult:
        if self.phase == "game_over":
            return {"error": "game already over"}
        self.winner = self._opponent(player_id)
        self.phase = "game_over"
        self._phase_end.set()
        return {"ok": True}

    def _act_lock(self, player: PlayerState, action: Message) -> ActionResult:
        player.locked = True

        if all(p.locked for p in self.players.values()):
            self._phase_end.set()

        return {"ok": True}

    def _opponent(self, player_id: str) -> str:
        return next(pid for pid in self.player_order if pid != player_id)
