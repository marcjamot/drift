import asyncio
import logging
import uuid
from typing import Awaitable, Callable, Dict, List, Optional, Tuple

from ..match import Match
from ..player import PlayerState

logger = logging.getLogger(__name__)

Sender = Callable[[str], Awaitable[None]]
_QueueEntry = Tuple[str, str, Sender]  # (player_id, name, send_fn)

MATCH_SIZE = 8
_BOT_NAMES = ["Grimshaw", "Vexara", "Ironpelt", "Solkar", "Brindle", "Mox", "Tesh"]


class Matchmaker:
    """Queues players and immediately pairs each into a match with 7 bots."""

    def __init__(self) -> None:
        self._queue: List[_QueueEntry] = []
        self._matches: Dict[str, Match] = {}         # match_id → Match
        self._player_to_match: Dict[str, str] = {}   # player_id → match_id
        self._lock = asyncio.Lock()

    async def queue(
        self, player_id: str, name: str, send_fn: Sender
    ) -> Optional[Match]:
        """Add player to the queue; immediately creates a match with 7 bots."""
        async with self._lock:
            self._queue.append((player_id, name, send_fn))
            entry: _QueueEntry = self._queue.pop(0)
            return self._create_match_with_bots(entry)

    def _create_match_with_bots(self, human: _QueueEntry) -> Match:
        pid, name, send_fn = human

        match_id: str = str(uuid.uuid4())
        players: List[PlayerState] = [
            PlayerState(player_id=pid, name=name, is_bot=False)
        ]
        for i in range(MATCH_SIZE - 1):
            bot_id = f"bot_{uuid.uuid4().hex[:8]}"
            players.append(PlayerState(player_id=bot_id, name=_BOT_NAMES[i], is_bot=True))

        match: Match = Match(match_id=match_id, players=players)
        match.register_sender(pid, send_fn)
        # Bots have no WS connection — no sender registered for them

        self._matches[match_id] = match
        self._player_to_match[pid] = match_id

        logger.info("Match %s: %s vs 7 bots", match_id[:8], name)
        return match

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

    def dequeue(self, player_id: str) -> None:
        """Remove a player from the queue (e.g. on disconnect before match start)."""
        self._queue = [e for e in self._queue if e[0] != player_id]
