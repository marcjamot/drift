import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, List

logger = logging.getLogger(__name__)

REPLAY_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "replays")
ReplayEntry = dict[str, Any]


class ReplayLogger:
    """Records a match as a structured event log, saveable to JSON."""

    def __init__(self, match_id: str) -> None:
        self.match_id = match_id
        self.entries: List[ReplayEntry] = []

    def _append(self, entry: ReplayEntry) -> None:
        self.entries.append(entry)

    def log_match_start(self, match_id: str, player_ids: List[str], seed: int) -> None:
        self._append(
            {
                "event": "match_start",
                "match_id": match_id,
                "players": player_ids,
                "seed": seed,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    def log_phase(self, phase: str, round_num: int) -> None:
        self._append({"event": "phase", "phase": phase, "round": round_num})

    def log_action(self, player_id: str, action: str, data: ReplayEntry) -> None:
        self._append(
            {"event": "action", "player_id": player_id, "action": action, **data}
        )

    def log_event(self, event_type: str, data: Any) -> None:
        self._append({"event": event_type, "data": data})

    def log_combat(self, round_num: int, result: ReplayEntry) -> None:
        self._append(
            {
                "event": "combat",
                "round": round_num,
                "winner": result.get("winner"),
                "damage": result.get("damage"),
                "events": result.get("events", []),
            }
        )

    def log_match_end(self, winner_id: str | None) -> None:
        self._append(
            {
                "event": "match_end",
                "winner": winner_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    async def save(self) -> None:
        os.makedirs(REPLAY_DIR, exist_ok=True)
        path: str = os.path.join(REPLAY_DIR, f"{self.match_id}.json")
        try:
            with open(path, "w") as fh:
                json.dump({"match_id": self.match_id, "log": self.entries}, fh, indent=2)
            logger.info("Replay saved: %s", path)
        except Exception as exc:
            logger.error("Failed to save replay %s: %s", self.match_id, exc)
