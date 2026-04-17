from __future__ import annotations

import random
from collections.abc import Sequence
from typing import TypeVar

T = TypeVar("T")


class PairingService:
    def pair(
        self,
        players: Sequence[T],
        rng: random.Random | None = None,
    ) -> list[tuple[T, T]]:
        shuffled = list(players)
        if rng is None:
            random.shuffle(shuffled)
        else:
            rng.shuffle(shuffled)
        return [
            (shuffled[i], shuffled[i + 1])
            for i in range(0, len(shuffled) - 1, 2)
        ]
