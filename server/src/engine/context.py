from __future__ import annotations

import asyncio
import json
import logging
import math
import random
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from .event_bus import EventBus
from .models import CardCatalog, CardPool, Minion, PlayerState
from .protocols import IReplayLogger
from .store import Store

logger = logging.getLogger(__name__)
Sender = Callable[[str], Awaitable[None]]
Message = dict[str, Any]

_MMR_DELTAS: dict[int, int] = {
    1: 25, 2: 20, 3: 15, 4: 10,
    5: -10, 6: -15, 7: -20, 8: -25,
}


@dataclass
class MatchContext:
    match_id: str
    players: dict[str, PlayerState]
    player_order: list[str]
    round: int
    event_bus: EventBus
    pool: CardPool
    catalog: CardCatalog
    rng: random.Random
    replay: IReplayLogger
    store: Store = field(default_factory=Store)
    phase: str = "waiting"
    winner: str | None = None
    current_deadline: float | None = None
    combat_pairs: dict[str, str] = field(default_factory=dict)
    senders: dict[str, Sender] = field(default_factory=dict)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    phase_end: asyncio.Event = field(default_factory=asyncio.Event)
    state_context: StateContext | None = None
    current_state: Any = None
    hero_options: dict[str, list[Any]] = field(default_factory=dict)
    hero_selection_done: asyncio.Event = field(default_factory=asyncio.Event)
    hero_picks_remaining: set[str] = field(default_factory=set)
    notified_dead: set[str] = field(default_factory=set)
    addons: list[Any] = field(default_factory=list)
    # intent type → list of (handler, meta) registered for the current state
    _intent_registry: dict[str, list[tuple[Any, Any]]] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Emit — the single write path for addons and engine alike
    # ------------------------------------------------------------------

    def emit(
        self,
        action: str,
        data: dict[str, Any] | None = None,
        store: dict[str, Any] | None = None,
        *,
        visible_to: list[str] | None = None,
    ) -> None:
        delta = store or {}
        if delta:
            self.store._apply(delta)
        self.replay.record_action(action, data or {}, store=delta, visible_to=visible_to)

    # ------------------------------------------------------------------
    # Intent dispatch — routes inbound client messages to addon handlers
    # ------------------------------------------------------------------

    def dispatch_intent(self, player_id: str, action: dict[str, Any]) -> dict[str, Any] | None:
        """Try registered intent handlers for the current state. Returns result or None."""
        kind = action.get("type", "")
        handlers = self._intent_registry.get(kind, [])
        ctx = self.state_context
        if ctx is None:
            return None
        for handler, _meta in handlers:
            handler(player_id, action, ctx)
            return {"ok": True}
        return None

    # ------------------------------------------------------------------
    # Player helpers
    # ------------------------------------------------------------------

    def human_players(self) -> list[str]:
        return [pid for pid in self.player_order if not self.players[pid].is_bot]

    def alive_players(self) -> list[str]:
        return [
            pid for pid in self.player_order
            if self.players[pid].health > 0 and not self.players[pid].ghost
        ]

    def ghost_players(self) -> list[str]:
        return sorted(
            [pid for pid in self.player_order if self.players[pid].ghost],
            key=lambda pid: (
                self.players[pid].eliminated_round or 0,
                self.player_order.index(pid),
            ),
            reverse=True,
        )

    # ------------------------------------------------------------------
    # WebSocket
    # ------------------------------------------------------------------

    def register_sender(self, player_id: str, send_fn: Sender) -> None:
        self.senders[player_id] = send_fn

    def unregister_sender(self, player_id: str) -> None:
        self.senders.pop(player_id, None)

    async def send_to(self, player_id: str, msg: Message) -> None:
        fn = self.senders.get(player_id)
        if fn:
            try:
                await fn(json.dumps(msg))
            except Exception as exc:
                logger.warning("Send to %s failed: %s", player_id, exc)

    async def broadcast(self, msg: Message) -> None:
        for pid in self.human_players():
            await self.send_to(pid, msg)

    async def send_state(self, player_id: str) -> None:
        player = self.players[player_id]
        if player.is_bot:
            return
        opp_id = self.combat_pairs.get(player_id)
        opponent = self.players[opp_id] if opp_id else None
        seconds_left = None
        if self.current_deadline is not None:
            seconds_left = max(0, math.ceil(self.current_deadline - time.monotonic()))
        leaderboard = sorted(
            [
                {
                    "player_id": p.player_id,
                    "name": p.name,
                    "health": p.health,
                    "armor": p.armor,
                    "is_bot": p.is_bot,
                    "is_ghost": p.ghost,
                    "last_combat_board": p.last_combat_board,
                }
                for p in self.players.values()
            ],
            key=lambda row: (-row["health"], row["name"]),
        )
        await self.send_to(
            player_id,
            {
                "type": "state",
                "match_id": self.match_id,
                "round": self.round,
                "phase": self.phase,
                "winner": self.winner,
                "deadline": self.current_deadline,
                "seconds_left": seconds_left,
                "buy_seconds_left": seconds_left if self.phase == "shop" else None,
                "self": self._player_payload(player, as_self=True),
                "opponent": self._player_payload(opponent, as_self=False) if opponent else None,
                "leaderboard": leaderboard,
            },
        )

    async def broadcast_state(self) -> None:
        for pid in self.human_players():
            await self.send_state(pid)

    # ------------------------------------------------------------------
    # State transitions
    # ------------------------------------------------------------------

    def enter_state(self, state_context: StateContext) -> None:
        # Clear all state-scoped memory keys from the previous state
        self.store.clear_prefix("_state:")
        # Reset the intent registry for the new state
        self._intent_registry.clear()

        self.state_context = state_context
        for addon in self.addons:
            addon._dispatch_state(state_context, self.event_bus)
            addon._dispatch_intents(state_context, self._intent_registry)
        for player in self.players.values():
            if player.hero:
                hero_subject = self._hero_subject(player)
                player.hero.on_state(hero_subject, state_context)
            for minion in [*player.board, *player.hand, *(m for m in player.shop if m)]:
                card = self.catalog.maybe_get(minion.card_id)
                if card:
                    card.on_state(minion, state_context)

    # ------------------------------------------------------------------
    # Game mechanics helpers
    # ------------------------------------------------------------------

    def apply_player_damage(self, player: PlayerState, amount: int) -> None:
        absorbed = min(player.armor, amount)
        if absorbed:
            new_armor = player.armor - absorbed
            player.armor = new_armor
            self.emit("player.armor", {
                "player_id": player.player_id,
                "value": new_armor,
            }, {f"player:{player.player_id}:armor": new_armor})
        damage = amount - absorbed
        if damage:
            new_health = player.health - damage
            player.health = new_health
            self.emit("player.health", {
                "player_id": player.player_id,
                "value": new_health,
            }, {f"player:{player.player_id}:health": new_health})

    def assign_placements_for_dead(self, newly_dead: list[str]) -> None:
        alive_after = sum(1 for p in self.players.values() if p.health > 0)
        for offset, pid in enumerate(newly_dead):
            self.players[pid].eliminated_round = self.round
            self.players[pid].placement = alive_after + len(newly_dead) - offset
            self.players[pid].ghost = True

    async def notify_eliminations(self) -> None:
        for pid in self.human_players():
            if pid in self.notified_dead:
                continue
            player = self.players[pid]
            if player.health <= 0 and player.placement is not None:
                mmr_delta = _MMR_DELTAS.get(player.placement, -25)
                player.mmr += mmr_delta
                self.notified_dead.add(pid)
                await self.send_to(pid, {
                    "type": "game_over",
                    "winner": self.winner,
                    "placement": player.placement,
                    "mmr_delta": mmr_delta,
                })

    async def notify_survivors_game_over(self) -> None:
        for pid in self.human_players():
            if pid in self.notified_dead:
                continue
            player = self.players[pid]
            placement = player.placement or 1
            mmr_delta = _MMR_DELTAS.get(placement, 25)
            player.mmr += mmr_delta
            self.notified_dead.add(pid)
            await self.send_to(pid, {
                "type": "game_over",
                "winner": self.winner,
                "placement": placement,
                "mmr_delta": mmr_delta,
            })

    def _hero_subject(self, player: PlayerState) -> Minion:
        if player.hero_subject is None or player.hero_subject.card_id != player.hero.id:  # type: ignore[union-attr]
            subject = player.hero.create_instance()  # type: ignore[union-attr]
            player.hero_subject = subject
            self.store._set(f"minion:{subject.instance_id}:owner_id", player.player_id)
        return player.hero_subject  # type: ignore[return-value]

    def _player_payload(self, player: PlayerState, *, as_self: bool) -> dict[str, Any]:
        payload = player.to_dict(as_self=as_self)
        payload["board"] = player.last_combat_board if player.ghost else [
            minion.to_dict(self._minion_extras(minion)) for minion in player.board
        ]
        if as_self:
            payload["hand"] = [minion.to_dict(self._minion_extras(minion)) for minion in player.hand]
            payload["shop"] = [
                minion.to_dict(self._minion_extras(minion)) if minion else None
                for minion in player.shop
            ]
        return payload

    def _minion_extras(self, minion: Minion) -> dict[str, Any]:
        _top_level = frozenset({"attack", "health", "golden"})
        return {
            k: v for k, v in self.store.prefix(f"minion:{minion.instance_id}:").items()
            if k not in _top_level
        }


# ---------------------------------------------------------------------------
# State context types
# ---------------------------------------------------------------------------

@dataclass
class StateContext:
    type: str
    match: MatchContext

    def __post_init__(self) -> None:
        # Pending store deltas from memory writes, flushed on ctx.emit(Action)
        self._pending: dict[str, Any] = {}

    @property
    def store(self) -> Store:
        return self.match.store

    def memory_match(self, addon: Any, subject: Any = None) -> Any:
        """Typed proxy for match-wide memory. Persists across state transitions.

        Pass ``self`` for read/write access to your own addon's memory.
        Pass another addon's class for read-only access to its memory.

        Args:
            addon:   ``self`` (own addon, writable) or another addon class (read-only).
            subject: A ``Minion`` for per-minion fields, a ``PlayerState`` for per-player
                     fields, or omit for global match-scoped fields.

        Example::

            mem = ctx.memory_match(self, payload.subject)   # per-minion
            mem = ctx.memory_match(self)                    # match-global
            mem = ctx.memory_match(DivineShieldAddon, minion)  # cross-addon, read-only
        """
        from .memory import MemoryProxy, _build_prefix
        is_class = isinstance(addon, type)
        addon_cls: type = addon if is_class else type(addon)
        schema = addon_cls.MatchMemory
        prefix = _build_prefix(addon_cls.id, "match", subject)
        return MemoryProxy(self.match.store, prefix, schema, self._pending, readonly=is_class)

    def memory_state(self, addon: Any, subject: Any = None) -> Any:
        """Typed proxy for state-scoped memory. Cleared on every state transition.

        Args:
            addon:   ``self`` (own addon, writable) or another addon class (read-only).
            subject: A ``Minion`` for per-minion fields, a ``PlayerState`` for per-player
                     fields, or omit for global state-scoped fields.

        Example::

            state = ctx.memory_state(self)                  # state-global counter
            state = ctx.memory_state(self, payload.subject) # per-minion, resets each state
        """
        from .memory import MemoryProxy, _build_prefix
        is_class = isinstance(addon, type)
        addon_cls: type = addon if is_class else type(addon)
        schema = addon_cls.StateMemory
        prefix = _build_prefix(addon_cls.id, "state", subject)
        return MemoryProxy(self.match.store, prefix, schema, self._pending, readonly=is_class)

    def emit(
        self,
        action: Any,
        data: dict[str, Any] | None = None,
        store: dict[str, Any] | None = None,
        *,
        visible_to: list[str] | None = None,
    ) -> None:
        """Emit an action to the replay log and client.

        Typed path (preferred): pass an ``Action`` subclass instance.
        Pending memory writes are automatically flushed into the log entry.
        An optional ``store`` dict merges additional raw deltas (e.g. modifying
        another minion's health) into the same log entry::

            ctx.emit(DivineShieldBroken(target_id=minion.instance_id))
            ctx.emit(PoisonousKill(source_id=..., target_id=...), store={f"minion:{id}:health": 0})

        Legacy path: pass a string action type directly (used by engine internals
        and card ``on_state`` hooks). Pending memory deltas are NOT flushed::

            ctx.emit("keyword.add", {"keyword": "divine_shield", ...}, {key: True})
        """
        from .actions import Action as ActionBase
        if isinstance(action, ActionBase):
            delta = {**self._pending, **(store or {})}
            self._pending.clear()
            self.match.emit(action.action_type, action._to_data(), delta or None, visible_to=visible_to)
        else:
            self.match.emit(action, data, store, visible_to=visible_to)


@dataclass(init=False)
class ShopStateContext(StateContext):
    def __init__(self, match: MatchContext) -> None:
        super().__init__(type="shop", match=match)


@dataclass(init=False)
class CombatStateContext(StateContext):
    friendly_board: list[Minion] = field(default_factory=list)
    enemy_board: list[Minion] = field(default_factory=list)

    def __init__(
        self,
        match: MatchContext,
        friendly_board: list[Minion] | None = None,
        enemy_board: list[Minion] | None = None,
    ) -> None:
        super().__init__(type="combat", match=match)
        self.friendly_board = friendly_board or []
        self.enemy_board = enemy_board or []
