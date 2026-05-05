from __future__ import annotations

from typing import Any


class Store:
    """Flat key-value store for all match state. The single source of truth.

    Reads are open to everyone. Writes from engine internals use _set()/_apply()
    directly; addon writes go through ctx.emit() which calls _apply() and logs.
    """

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def _set(self, key: str, value: Any) -> None:
        """Direct write — engine internals only, not logged."""
        self._data[key] = value

    def _apply(self, delta: dict[str, Any]) -> None:
        """Apply a store delta from ctx.emit() — called by MatchContext."""
        self._data.update(delta)

    def snapshot(self) -> dict[str, Any]:
        return dict(self._data)

    def prefix(self, pfx: str) -> dict[str, Any]:
        """All entries whose key starts with pfx, with the prefix stripped."""
        return {k.removeprefix(pfx): v for k, v in self._data.items() if k.startswith(pfx)}

    def clear_prefix(self, pfx: str) -> None:
        """Remove all keys starting with pfx (used to clear state-scoped memory on transition)."""
        for k in [k for k in self._data if k.startswith(pfx)]:
            del self._data[k]
