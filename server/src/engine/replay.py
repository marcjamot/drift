from __future__ import annotations

import json
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .context import MatchContext
    from .state_machine import State


class ReplayLogger:
    def __init__(self, match_id: str, seed: int, path: Path | None = None) -> None:
        self.path = path
        self.started_at = time.monotonic()
        self.seq = 0
        self.metadata: dict[str, Any] = {"version": 2, "match_id": match_id, "seed": seed}
        self.states: list[dict[str, Any]] = []
        self.current_state: dict[str, Any] | None = None

    def set_metadata(self, **values: Any) -> None:
        self.metadata.update(self._json_safe(values))

    def begin_state(self, ctx: "MatchContext", state: "State") -> None:
        self.end_state()
        entry: dict[str, Any] = {
            "id": len(self.states),
            "name": state.name,
            "type": state.type,
            "round": ctx.round,
            "entered_at": self.now(),
            "deadline": self.replay_time(ctx.current_deadline),
            "snapshots": self._snapshots(ctx),
            "actions": [],
            "exited_at": None,
        }
        self.states.append(entry)
        self.current_state = entry

    def end_state(self) -> None:
        if self.current_state is not None and self.current_state.get("exited_at") is None:
            self.current_state["exited_at"] = self.now()
        self.current_state = None

    def update_current_snapshot(self, ctx: "MatchContext") -> None:
        if self.current_state is not None:
            self.current_state["round"] = ctx.round
            self.current_state["deadline"] = self.replay_time(ctx.current_deadline)
            self.current_state["snapshots"] = self._snapshots(ctx)

    def record_action(
        self,
        action_type: str,
        data: dict[str, Any],
        store: dict[str, Any] | None = None,
        *,
        visible_to: list[str] | None = None,
    ) -> dict[str, Any]:
        self.seq += 1
        action: dict[str, Any] = {
            "seq": self.seq,
            "at": self.now(),
            "type": action_type,
            "data": self._json_safe(data),
            "store": self._json_safe(store or {}),
        }
        if visible_to is not None:
            action["visible_to"] = visible_to
        if self.current_state is None:
            self._bootstrap_state()
        self.current_state["actions"].append(action)  # type: ignore[index]
        return action

    def _snapshots(self, ctx: "MatchContext") -> dict[str, Any]:
        result: dict[str, Any] = {
            "__spectator": self._spectator_snapshot(ctx),
        }
        for player_id in ctx.players:
            result[player_id] = self._player_snapshot(ctx, player_id)
        return result

    def _spectator_snapshot(self, ctx: "MatchContext") -> dict[str, Any]:
        return {
            "match_id": ctx.match_id,
            "round": ctx.round,
            "phase": ctx.phase,
            "winner": ctx.winner,
            "deadline": self.replay_time(ctx.current_deadline),
            "combat_pairs": dict(ctx.combat_pairs),
            "players": {
                pid: player.to_dict(as_self=True)
                for pid, player in ctx.players.items()
            },
            "leaderboard": self._leaderboard(ctx),
        }

    def _player_snapshot(self, ctx: "MatchContext", viewer_id: str) -> dict[str, Any]:
        snap: dict[str, Any] = {
            "match_id": ctx.match_id,
            "round": ctx.round,
            "phase": ctx.phase,
            "winner": ctx.winner,
            "deadline": self.replay_time(ctx.current_deadline),
            "combat_pairs": dict(ctx.combat_pairs),
            "players": {},
            "leaderboard": self._leaderboard(ctx),
        }
        for pid, player in ctx.players.items():
            if pid == viewer_id:
                snap["players"][pid] = player.to_dict(as_self=True)
            else:
                snap["players"][pid] = player.to_dict(as_self=False)
        return snap

    def _leaderboard(self, ctx: "MatchContext") -> list[dict[str, Any]]:
        return [
            {
                "player_id": p.player_id,
                "name": p.name,
                "health": p.health,
                "armor": p.armor,
                "is_bot": p.is_bot,
                "is_ghost": p.ghost,
                "placement": p.placement,
            }
            for p in ctx.players.values()
        ]

    def replay_state_at(
        self,
        replay_time: float,
        *,
        viewer_id: str = "__spectator",
    ) -> dict[str, Any] | None:
        relevant = [s for s in self.states if s["entered_at"] <= replay_time]
        if not relevant:
            return None
        state = relevant[-1]
        visible_actions = [
            a for a in state["actions"]
            if a["at"] <= replay_time
            and (a.get("visible_to") is None or viewer_id in a["visible_to"])
        ]
        return {
            "state": state,
            "snapshot": state["snapshots"].get(viewer_id, state["snapshots"]["__spectator"]),
            "actions": visible_actions,
        }

    def _bootstrap_state(self) -> None:
        self.states.append({
            "id": len(self.states),
            "name": "bootstrap", "type": "bootstrap",
            "round": 0, "entered_at": 0.0,
            "deadline": None, "snapshots": {}, "actions": [], "exited_at": None,
        })
        self.current_state = self.states[-1]

    def now(self) -> float:
        return round(time.monotonic() - self.started_at, 4)

    def replay_time(self, timestamp: float | None) -> float | None:
        return None if timestamp is None else round(timestamp - self.started_at, 4)

    def to_dict(self) -> dict[str, Any]:
        return {"metadata": self.metadata, "states": self.states}

    def flush(self) -> None:
        self.end_state()
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    def _json_safe(self, value: object) -> Any:
        if isinstance(value, dict):
            return {str(k): self._json_safe(v) for k, v in value.items()}
        if isinstance(value, (list, tuple, set, frozenset)):
            return [self._json_safe(i) for i in value]
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        if hasattr(value, "to_dict"):
            return self._json_safe(value.to_dict())
        return repr(value)
