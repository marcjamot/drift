from __future__ import annotations

from typing import Any

from .models import PlayerState


def choose_shop_actions(player: PlayerState) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    while player.gold >= 3 and len(player.hand) + len(player.board) < 7:
        buy_index = next((idx for idx, minion in enumerate(player.shop) if minion is not None), None)
        if buy_index is None:
            break
        actions.append({"type": "buy", "shop_index": buy_index})
        actions.append({"type": "play", "hand_index": len(player.hand)})
        break
    actions.append({"type": "lock"})
    return actions
