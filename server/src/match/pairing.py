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
        ghosts: Sequence[T] = (),
    ) -> list[tuple[T, T]]:
        shuffled = list(players)
        if rng is None:
            random.shuffle(shuffled)
        else:
            rng.shuffle(shuffled)
        pairs = [
            (shuffled[i], shuffled[i + 1])
            for i in range(0, len(shuffled) - 1, 2)
        ]
        if len(players) < 4 and len(shuffled) % 2 == 1 and ghosts:
            pairs.append((shuffled[-1], ghosts[0]))
        return pairs
