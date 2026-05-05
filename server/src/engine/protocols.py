from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class IReplayLogger(Protocol):
    def begin_state(self, ctx: Any, state: Any) -> None: ...
    def end_state(self) -> None: ...
    def update_current_snapshot(self, ctx: Any) -> None: ...
    def record_action(
        self,
        action_type: str,
        data: dict[str, Any],
        store: dict[str, Any] | None = None,
        *,
        visible_to: list[str] | None = None,
    ) -> dict[str, Any]: ...
    def flush(self) -> None: ...
