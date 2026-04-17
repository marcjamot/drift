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

logger = logging.getLogger(__name__)

Message = dict[str, Any]
ActionResult = dict[str, Any]
Sender = Callable[[str], Awaitable[None]]

HERO_SELECTION_TIMEOUT = 30.0  # seconds players have to pick a hero
HERO_OPTIONS_COUNT = 3         # choices offered to each player


class Match:
    """
    Orchestrates a single 2-player match.

    Game loop:
        Hero selection → match_start broadcast
        while not game_over:
            BuyPhase.enter()   → set state, refresh shops, start buy timer
            BuyPhase.wait()    → block until timer expires or both players lock
            CombatPhase.enter()→ broadcast combat_start
            CombatPhase.wait() → resolve fight, apply damage, display delay
        broadcast game_over

    The buy timer only starts inside BuyPhase.enter(), which is only reached
    after CombatPhase.wait() fully returns.  This guarantees the purchase
    window never opens while a battle result is still being displayed.
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
        self._current_phase: Optional[Phase] = None

        # Hero selection state
        self._hero_options: Dict[str, List[HeroDef]] = {}
        self._hero_selection_done: asyncio.Event = asyncio.Event()
        self._hero_picks_remaining: set = set()

    # ── sender registry ───────────────────────────────────────────────────────

    def register_sender(self, player_id: str, send_fn: Sender) -> None:
        self._senders[player_id] = send_fn

    def unregister_sender(self, player_id: str) -> None:
        self._senders.pop(player_id, None)

    # ── messaging ─────────────────────────────────────────────────────────────

    async def send_to(self, player_id: str, msg: Message) -> None:
        fn = self._senders.get(player_id)
        if fn:
            try:
                await fn(json.dumps(msg))
            except Exception as exc:
                logger.warning("Send to %s failed: %s", player_id, exc)

    async def broadcast(self, msg: Message) -> None:
        for pid in self.player_order:
            await self.send_to(pid, msg)

    async def send_state(self, player_id: str) -> None:
        player = self.players[player_id]
        opp_id = self._opponent(player_id)
        opp = self.players[opp_id]

        buy_seconds_left: Optional[int] = None
        if self.phase == "buy" and self._buy_phase_started_at is not None:
            buy_seconds_left = max(
                0,
                math.ceil(BUY_TIMER - (time.monotonic() - self._buy_phase_started_at)),
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

    # ── game loop ─────────────────────────────────────────────────────────────

    async def run(self) -> None:
        # ── hero selection ────────────────────────────────────────────────────
        self._hero_options = self._deal_hero_options()
        self._hero_picks_remaining = set(self.player_order)
        self._hero_selection_done.clear()

        for pid in self.player_order:
            await self.send_to(pid, {
                "type": "hero_options",
                "options": [h.to_dict() for h in self._hero_options[pid]],
            })

        try:
            await asyncio.wait_for(
                self._hero_selection_done.wait(), timeout=HERO_SELECTION_TIMEOUT
            )
        except asyncio.TimeoutError:
            # Auto-pick first option for anyone who didn't choose in time
            for pid in list(self._hero_picks_remaining):
                self.players[pid].hero = self._hero_options[pid][0]
            self._hero_picks_remaining.clear()

        # ── notify both players the match is starting ─────────────────────────
        for pid in self.player_order:
            opp_id = self._opponent(pid)
            await self.send_to(pid, {
                "type": "match_start",
                "match_id": self.match_id,
                "opponent": self.players[opp_id].name,
            })

        # ── game loop ─────────────────────────────────────────────────────────
        for player in self.players.values():
            self._buy_phase._refresh_shop(player, self)

        while self.phase != "game_over":
            self._current_phase = self._buy_phase
            await self._buy_phase.enter(self)
            await self._buy_phase.wait(self)

            if self.phase == "game_over":
                break

            self._current_phase = self._combat_phase
            await self._combat_phase.enter(self)
            await self._combat_phase.wait(self)

        self._current_phase = None
        await self.broadcast({"type": "game_over", "winner": self.winner})

    # ── action dispatch ───────────────────────────────────────────────────────

    async def handle_action(self, player_id: str, action: Message) -> ActionResult:
        async with self._lock:
            kind = action.get("type")

            if kind == "concede":
                return self._act_concede(player_id)

            if kind == "hero_pick":
                return self._act_hero_pick(player_id, action)

            if self._current_phase is None:
                return {"error": "match not started"}

            result = await self._current_phase.handle_action(player_id, action, self)

            if result.get("ok"):
                for pid in self.player_order:
                    await self.send_state(pid)
                player = self.players.get(player_id)
                if player and player.pending_discover:
                    await self.send_to(player_id, {
                        "type": "discover",
                        "options": [m.to_dict() for m in player.pending_discover],
                    })

            return result

    def _act_concede(self, player_id: str) -> ActionResult:
        if self.phase == "game_over":
            return {"error": "game already over"}
        self.winner = self._opponent(player_id)
        self.phase = "game_over"
        self._phase_end.set()
        return {"ok": True}

    # ── hero selection helpers ────────────────────────────────────────────────

    def _deal_hero_options(self) -> Dict[str, List[HeroDef]]:
        """Sample distinct heroes for each player — no shared options."""
        needed = len(self.player_order) * HERO_OPTIONS_COUNT
        pool = self.rng.sample(HERO_POOL, min(needed, len(HERO_POOL)))
        options: Dict[str, List[HeroDef]] = {}
        for i, pid in enumerate(self.player_order):
            options[pid] = pool[i * HERO_OPTIONS_COUNT:(i + 1) * HERO_OPTIONS_COUNT]
        return options

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

    # ── helpers ───────────────────────────────────────────────────────────────

    def _opponent(self, player_id: str) -> str:
        return next(pid for pid in self.player_order if pid != player_id)
