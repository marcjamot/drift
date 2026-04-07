import asyncio
import logging
import uuid
from typing import Awaitable, Callable, Dict, List, Optional, Tuple

from ..match import Match
from ..player import PlayerState

logger = logging.getLogger(__name__)

Sender = Callable[[str], Awaitable[None]]
_QueueEntry = Tuple[str, str, Sender]  # (player_id, name, send_fn)


class Matchmaker:
    """Queues players and pairs them into matches."""

    def __init__(self) -> None:
        self._queue: List[_QueueEntry] = []
        self._matches: Dict[str, Match] = {}         # match_id → Match
        self._player_to_match: Dict[str, str] = {}   # player_id → match_id
        self._lock = asyncio.Lock()

    async def queue(
        self, player_id: str, name: str, send_fn: Sender
    ) -> Optional[Match]:
        """
        Add player to the queue.  Returns a Match if pairing was possible,
        otherwise None (player waits in queue).
        """
        async with self._lock:
            self._queue.append((player_id, name, send_fn))

            if len(self._queue) >= 2:
                p1: _QueueEntry = self._queue.pop(0)
                p2: _QueueEntry = self._queue.pop(0)
                return self._create_match(p1, p2)
        return None

    def _create_match(self, p1: _QueueEntry, p2: _QueueEntry) -> Match:
        pid1, name1, send1 = p1
        pid2, name2, send2 = p2

        match_id: str = str(uuid.uuid4())
        players: List[PlayerState] = [
            PlayerState(player_id=pid1, name=name1),
            PlayerState(player_id=pid2, name=name2),
        ]

        match: Match = Match(match_id=match_id, players=players)
        match.register_sender(pid1, send1)
        match.register_sender(pid2, send2)

        self._matches[match_id] = match
        self._player_to_match[pid1] = match_id
        self._player_to_match[pid2] = match_id

        logger.info("Match %s: %s vs %s", match_id[:8], name1, name2)
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
