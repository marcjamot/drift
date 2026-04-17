import asyncio
import json
import logging
import math
import time
import uuid
from typing import Awaitable, Callable, Dict, List, Optional, Tuple

from ..match import Match
from ..player import PlayerState

logger = logging.getLogger(__name__)

Sender = Callable[[str], Awaitable[None]]
_QueueEntry = Tuple[str, str, Sender]  # (player_id, name, send_fn)

MATCH_SIZE = 8
FILL_WAIT_SECONDS = 30
_BOT_NAMES = ["Grimshaw", "Vexara", "Ironpelt", "Solkar", "Brindle", "Mox", "Tesh"]


class Matchmaker:
    def __init__(self, *, auto_start_matches: bool = True) -> None:
        self._queue: List[_QueueEntry] = []
        self._matches: Dict[str, Match] = {}         # match_id → Match
        self._player_to_match: Dict[str, str] = {}   # player_id → match_id
        self._lock = asyncio.Lock()
        self._fill_task: Optional[asyncio.Task[None]] = None
        self._fill_started_at: Optional[float] = None
        self._auto_start_matches = auto_start_matches
        self._match_tasks: set[asyncio.Task[None]] = set()

    async def queue(
        self, player_id: str, name: str, send_fn: Sender
    ) -> Optional[Match]:
        async with self._lock:
            for i, entry in enumerate(self._queue):
                if entry[0] == player_id:
                    self._queue[i] = (player_id, name, send_fn)
                    await self._broadcast_queue_state()
                    return None

            self._queue.append((player_id, name, send_fn))
            if len(self._queue) == 1:
                self._fill_started_at = time.monotonic()
                self._fill_task = asyncio.create_task(self._fill_after_wait())

            if len(self._queue) >= MATCH_SIZE:
                match = self._create_match_from_queue_locked()
                self._start_match(match)
                return match

            await self._broadcast_queue_state()
            return None

    async def skip_wait(self, player_id: str) -> Optional[Match]:
        async with self._lock:
            if len(self._queue) != 1 or self._queue[0][0] != player_id:
                return None
            match = self._create_match_from_queue_locked()
            self._start_match(match)
            return match

    async def fill_pending_queue(self) -> Optional[Match]:
        async with self._lock:
            if not self._queue:
                return None
            match = self._create_match_from_queue_locked()
            self._start_match(match)
            return match

    async def _fill_after_wait(self) -> None:
        await asyncio.sleep(FILL_WAIT_SECONDS)
        await self.fill_pending_queue()

    def _create_match_from_queue_locked(self) -> Match:
        humans = self._queue[:MATCH_SIZE]
        self._queue = self._queue[MATCH_SIZE:]
        if self._fill_task and self._fill_task is not asyncio.current_task():
            self._fill_task.cancel()
        self._fill_task = None
        self._fill_started_at = None
        return self._create_match_with_bots(humans)

    def _create_match_with_bots(self, humans: List[_QueueEntry]) -> Match:
        match_id: str = str(uuid.uuid4())
        players: List[PlayerState] = [
            PlayerState(player_id=pid, name=name, is_bot=False)
            for pid, name, _send_fn in humans
        ]
        for i in range(MATCH_SIZE - len(humans)):
            bot_id = f"bot_{uuid.uuid4().hex[:8]}"
            players.append(PlayerState(player_id=bot_id, name=_BOT_NAMES[i % len(_BOT_NAMES)], is_bot=True))

        match: Match = Match(match_id=match_id, players=players)
        for pid, _name, send_fn in humans:
            match.register_sender(pid, send_fn)

        self._matches[match_id] = match
        for pid, _name, _send_fn in humans:
            self._player_to_match[pid] = match_id

        logger.info("Match %s: %d humans, %d bots", match_id[:8], len(humans), MATCH_SIZE - len(humans))
        return match

    def _start_match(self, match: Match) -> None:
        if not self._auto_start_matches:
            return
        task = asyncio.create_task(match.run())
        self._match_tasks.add(task)
        task.add_done_callback(self._match_tasks.discard)

    async def _broadcast_queue_state(self) -> None:
        if not self._queue:
            return
        seconds_left = FILL_WAIT_SECONDS
        if self._fill_started_at is not None:
            seconds_left = max(
                0,
                math.ceil(FILL_WAIT_SECONDS - (time.monotonic() - self._fill_started_at)),
            )
        msg = {
            "type": "queued",
            "queued_count": len(self._queue),
            "total_slots": MATCH_SIZE,
            "seconds_left": seconds_left,
            "can_skip_wait": len(self._queue) == 1,
        }
        for _pid, _name, send_fn in self._queue:
            await send_fn(json.dumps(msg))

    def get_match_for_player(self, player_id: str) -> Optional[Match]:
        mid: str | None = self._player_to_match.get(player_id)
        return self._matches.get(mid) if mid else None

    def get_match(self, match_id: str) -> Optional[Match]:
        return self._matches.get(match_id)

    def cleanup_match(self, match_id: str) -> None:
        match: Match | None = self._matches.pop(match_id, None)
        if match:
            for pid in match.player_order:
                self._player_to_match.pop(pid, None)

    async def dequeue(self, player_id: str) -> None:
        async with self._lock:
            before = len(self._queue)
            self._queue = [e for e in self._queue if e[0] != player_id]
            if not self._queue:
                if self._fill_task:
                    self._fill_task.cancel()
                self._fill_task = None
                self._fill_started_at = None
            elif len(self._queue) != before:
                await self._broadcast_queue_state()
