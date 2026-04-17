import asyncio
import json
import logging
import math
import random
import time
from typing import Any, Awaitable, Callable, Dict, List, Optional

from ..cards.catalog import SHOP_CARDS
from ..cards.pool import CardPool
from ..heroes.base import HeroDef
from ..heroes.catalog import HERO_POOL
from ..player import PlayerState
from .phases.base import Phase
from .phases.buy_phase import BuyPhase, DURATION as BUY_TIMER
from .phases.combat_phase import CombatPhase
from .pairing import PairingService

logger = logging.getLogger(__name__)

Message = dict[str, Any]
ActionResult = dict[str, Any]
Sender = Callable[[str], Awaitable[None]]

HERO_SELECTION_TIMEOUT = 30.0  # seconds players have to pick a hero
HERO_OPTIONS_COUNT = 3         # choices offered to the human player

# MMR change per placement (1 = winner, 8 = first eliminated)
_MMR_DELTAS: Dict[int, int] = {
    1: 25, 2: 20, 3: 15, 4: 10,
    5: -10, 6: -15, 7: -20, 8: -25,
}


class Match:
    """
    Orchestrates an 8-player match (1 human + 7 bots).

    Game loop:
        Hero selection (human only) → match_start broadcast
        while not game_over:
            _compute_combat_pairs()          → 1v1 pairings among alive players
            BuyPhase.enter()                 → bots act instantly; human gets timer
            BuyPhase.wait()                  → block until timer or human locks
            CombatPhase.enter()              → broadcast combat_start
            CombatPhase.wait()               → resolve all pairs; apply damage; notify dead humans
        broadcast game_over (final human survivor or winner)
    """

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

        self.pool: CardPool = CardPool(
            SHOP_CARDS, random.Random(self.seed ^ 0xDEAD)
        )

        self._senders: Dict[str, Sender] = {}
        self._lock = asyncio.Lock()
        self._phase_end = asyncio.Event()
        self._buy_phase_started_at: Optional[float] = None

        self._buy_phase = BuyPhase()
        self._combat_phase = CombatPhase()
        self._pairing_service = PairingService()
        self._current_phase: Optional[Phase] = None

        # Hero selection state
        self._hero_options: Dict[str, List[HeroDef]] = {}
        self._hero_selection_done: asyncio.Event = asyncio.Event()
        self._hero_picks_remaining: set = set()

        # 8-player state
        self._combat_pairs: Dict[str, str] = {}   # player_id → opponent_id this round
        self._notified_dead: set = set()           # player_ids already sent game_over

    # ── sender registry ───────────────────────────────────────────────────────

    def register_sender(self, player_id: str, send_fn: Sender) -> None:
        self._senders[player_id] = send_fn

    def unregister_sender(self, player_id: str) -> None:
        self._senders.pop(player_id, None)

    # ── helpers ───────────────────────────────────────────────────────────────

    def _human_players(self) -> List[str]:
        return [pid for pid in self.player_order if not self.players[pid].is_bot]

    def _alive_players(self) -> List[str]:
        return [
            pid for pid in self.player_order
            if self.players[pid].health > 0 and not self.players[pid].ghost
        ]

    def _ghost_players(self) -> List[str]:
        return sorted(
            [pid for pid in self.player_order if self.players[pid].ghost],
            key=lambda pid: (
                self.players[pid].eliminated_round or 0,
                self.player_order.index(pid),
            ),
            reverse=True,
        )

    def _compute_combat_pairs(self) -> None:
        pairs = self._pairing_service.pair(
            self._alive_players(),
            self.rng,
            self._ghost_players(),
        )
        self._combat_pairs = {}
        for player_id, opponent_id in pairs:
            self._combat_pairs[player_id] = opponent_id
            self._combat_pairs[opponent_id] = player_id

    @property
    def combat_pairs(self) -> dict[str, str]:
        """Read-only view of this round's player_id → opponent_id pairings."""
        return dict(self._combat_pairs)

    def apply_player_damage(self, player: PlayerState, amount: int) -> None:
        absorbed = min(player.armor, amount)
        player.armor -= absorbed
        player.health -= amount - absorbed

    # ── messaging ─────────────────────────────────────────────────────────────

    async def send_to(self, player_id: str, msg: Message) -> None:
        fn = self._senders.get(player_id)
        if fn:
            try:
                await fn(json.dumps(msg))
            except Exception as exc:
                logger.warning("Send to %s failed: %s", player_id, exc)

    async def _broadcast(self, msg: Message) -> None:
        for pid in self._human_players():
            await self.send_to(pid, msg)

    async def send_state(self, player_id: str) -> None:
        await self._send_state(player_id)

    async def _send_state(self, player_id: str) -> None:
        player = self.players[player_id]
        if player.is_bot:
            return

        opp_id = self._combat_pairs.get(player_id)
        opp = self.players[opp_id] if opp_id else None

        buy_seconds_left: Optional[int] = None
        if self.phase == "buy" and self._buy_phase_started_at is not None:
            buy_seconds_left = max(
                0,
                math.ceil(BUY_TIMER - (time.monotonic() - self._buy_phase_started_at)),
            )

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
            key=lambda x: (-x["health"], x["name"]),
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
                "opponent": opp.to_dict(as_self=False) if opp else None,
                "leaderboard": leaderboard,
            },
        )

    async def _broadcast_state(self) -> None:
        for pid in self._human_players():
            await self._send_state(pid)

    async def _send_hero_options(self, player_id: str) -> None:
        await self.send_to(player_id, {
            "type": "hero_options",
            "options": [h.to_dict() for h in self._hero_options[player_id]],
        })

    async def _broadcast_match_start(self) -> None:
        await self._broadcast({
            "type": "match_start",
            "match_id": self.match_id,
        })

    async def _broadcast_combat_start(self) -> None:
        await self._broadcast({"type": "combat_start", "round": self.round})

    async def _send_combat_log(
        self,
        player_id: str,
        player_a: str,
        player_b: str,
        initial_a: list[dict[str, Any]],
        initial_b: list[dict[str, Any]],
        result: dict[str, Any],
        opponent_is_ghost: bool,
    ) -> None:
        await self.send_to(player_id, {
            "type": "combat_log",
            "round": self.round,
            "players": [player_a, player_b],
            "is_ghost": opponent_is_ghost,
            "initial_a": initial_a,
            "initial_b": initial_b,
            "events": result["events"],
            "surviving_a": result["surviving_a"],
            "surviving_b": result["surviving_b"],
        })

    async def _send_combat_result(
        self,
        player_id: str,
        combat_result_payload: dict[str, Any],
    ) -> None:
        await self.send_to(player_id, {
            "type": "combat_result",
            "round": self.round,
            **combat_result_payload,
        })

    async def _send_discover(self, player_id: str) -> None:
        player = self.players[player_id]
        if player.is_bot:
            return
        await self.send_to(player_id, {
            "type": "discover_options",
            "options": [m.to_dict() for m in player.pending_discover],
        })

    async def _send_game_over(
        self,
        player_id: str,
        placement: int,
        mmr_delta: int,
    ) -> None:
        await self.send_to(player_id, {
            "type": "game_over",
            "winner": self.winner,
            "placement": placement,
            "mmr_delta": mmr_delta,
        })

    async def _notify_eliminations(self) -> None:
        for pid in self._human_players():
            if pid in self._notified_dead:
                continue
            player = self.players[pid]
            if player.health <= 0 and player.placement is not None:
                mmr_delta = _MMR_DELTAS.get(player.placement, -25)
                player.mmr += mmr_delta
                self._notified_dead.add(pid)
                await self._send_game_over(pid, player.placement, mmr_delta)

    async def _notify_surviving_humans_game_over(self) -> None:
        for pid in self._human_players():
            if pid in self._notified_dead:
                continue
            player = self.players[pid]
            placement = player.placement or 1
            mmr_delta = _MMR_DELTAS.get(placement, 25)
            player.mmr += mmr_delta
            self._notified_dead.add(pid)
            await self._send_game_over(pid, placement, mmr_delta)

    # ── game loop ─────────────────────────────────────────────────────────────

    async def run(self) -> None:
        # ── hero selection ────────────────────────────────────────────────────
        self._deal_hero_options()
        self._hero_picks_remaining = set(self._human_players())
        self._hero_selection_done.clear()

        for pid in self._hero_picks_remaining:
            await self._send_hero_options(pid)

        if self._hero_picks_remaining:
            try:
                await asyncio.wait_for(
                    self._hero_selection_done.wait(), timeout=HERO_SELECTION_TIMEOUT
                )
            except asyncio.TimeoutError:
                for pid in list(self._hero_picks_remaining):
                    self.players[pid].hero = self._hero_options[pid][0]
                self._hero_picks_remaining.clear()

        await self._broadcast_match_start()

        # ── initial shops ─────────────────────────────────────────────────────
        from .actions import refresh_shop
        for player in self.players.values():
            refresh_shop(player, self.pool)

        # ── game loop ─────────────────────────────────────────────────────────
        while self.phase != "game_over":
            self._compute_combat_pairs()

            self._current_phase = self._buy_phase
            await self._buy_phase.enter(self)
            await self._buy_phase.wait(self)

            if self.phase == "game_over":
                break

            self._current_phase = self._combat_phase
            await self._combat_phase.enter(self)
            await self._combat_phase.wait(self)

        self._current_phase = None

        await self._notify_surviving_humans_game_over()

    # ── action dispatch ───────────────────────────────────────────────────────

    async def handle_action(self, player_id: str, action: Message) -> ActionResult:
        async with self._lock:
            kind = action.get("type")

            if kind == "concede":
                return await self._act_concede(player_id)

            if kind == "hero_pick":
                return self._act_hero_pick(player_id, action)

            if self._current_phase is None:
                return {"error": "match not started"}

            result = await self._current_phase.handle_action(player_id, action, self)

            if result.get("ok"):
                for pid in self._human_players():
                    await self._send_state(pid)
                player = self.players.get(player_id)
                if player and player.pending_discover:
                    await self._send_discover(player_id)

            return result

    async def _act_concede(self, player_id: str) -> ActionResult:
        if self.phase == "game_over":
            return {"error": "game already over"}
        player = self.players[player_id]
        player.health = 0
        player.eliminated_round = self.round
        player.ghost = True
        alive_after = sum(1 for p in self.players.values() if p.health > 0)
        player.placement = alive_after + 1

        alive_players = self._alive_players()
        if len(alive_players) <= 1:
            self.winner = alive_players[0] if alive_players else None
            if self.winner:
                self.players[self.winner].placement = 1
            self.phase = "game_over"
            self._phase_end.set()
        return {"ok": True}

    # ── hero selection helpers ────────────────────────────────────────────────

    def _deal_hero_options(self) -> None:
        """Assign heroes to bots randomly; build pick options for humans."""
        self._hero_options = {}
        for pid in self.player_order:
            player = self.players[pid]
            if player.is_bot:
                player.hero = self.rng.choice(HERO_POOL)
            else:
                chosen = self.rng.sample(HERO_POOL, min(HERO_OPTIONS_COUNT, len(HERO_POOL)))
                self._hero_options[pid] = chosen

    def _act_hero_pick(self, player_id: str, action: Message) -> ActionResult:
        if player_id not in self._hero_picks_remaining:
            return {"error": "hero already chosen"}
        options = self._hero_options.get(player_id, [])
        idx = action.get("index")
        if idx is None or not (0 <= idx < len(options)):
            return {"error": "invalid hero index"}
        self.players[player_id].hero = options[idx]
        self._hero_picks_remaining.discard(player_id)
        if not self._hero_picks_remaining:
            self._hero_selection_done.set()
        return {"ok": True}

    # ── placement helpers ─────────────────────────────────────────────────────

    def assign_placements_for_dead(self, newly_dead: List[str]) -> None:
        """
        Called after combat each round.  Players in newly_dead all died this
        round and fill the next placement slots after the remaining alive players.
        The last surviving player will be assigned placement 1 at match end.
        """
        alive_after = sum(1 for p in self.players.values() if p.health > 0)
        for offset, pid in enumerate(newly_dead):
            self.players[pid].eliminated_round = self.round
            self.players[pid].placement = alive_after + len(newly_dead) - offset
            self.players[pid].ghost = True
