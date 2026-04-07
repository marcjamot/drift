from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from ..match import Match

Message = dict[str, Any]


class Phase(ABC):
    """
    Abstract base for a match phase.

    Subclasses define:
      - name        : phase identifier sent to clients
      - duration    : float seconds if the phase has a countdown, None otherwise
      - enter()     : set state, broadcast, start timers
      - wait()      : block until the phase naturally concludes
      - handle_action(): accept or reject player actions
    """

    name: str
    duration: Optional[float] = None  # None = no fixed countdown

    @abstractmethod
    async def enter(self, match: Match) -> None:
        """Transition into this phase: update state, notify clients."""
        ...

    @abstractmethod
    async def wait(self, match: Match) -> None:
        """Block until this phase is done (timer, condition, or both)."""
        ...

    async def handle_action(
        self, player_id: str, action: Message, match: Match
    ) -> Message:
        """Default: reject all actions. Override in phases that accept input."""
        return {"error": f"action not allowed during {self.name} phase"}
