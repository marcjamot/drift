from __future__ import annotations

import dataclasses
from typing import Any, ClassVar


class Action:
    """Base class for all emittable actions. Always use as a ``@dataclass``.

    Set ``action_type`` as a ClassVar — this becomes the event type string
    seen by client effect handlers. Fields become the action data payload.

    Example::

        @dataclass
        class DivineShieldBroken(Action):
            action_type: ClassVar[str] = "keyword.divine_shield_broken"
            target_id: str

    Emit via ``ctx.emit(DivineShieldBroken(target_id=minion.instance_id))``.
    Any pending memory writes are automatically flushed into the same log entry.
    """

    action_type: ClassVar[str]

    def _to_data(self) -> dict[str, Any]:
        if dataclasses.is_dataclass(self):
            return dataclasses.asdict(self)
        return {}
