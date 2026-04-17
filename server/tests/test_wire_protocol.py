"""
Wire protocol smoke tests.

These guard against the Python snapshot output silently dropping keys that
the TypeScript client depends on. They are not exhaustive type-checks — they
verify shape, not semantics. Update the expected key sets here whenever the
wire protocol intentionally changes.
"""
import asyncio

from src.cards.catalog import CARD_CATALOG
from src.match.match import Match
from src.player.player import PlayerState


_MINION_KEYS = {
    "instance_id", "card_id", "name", "description",
    "attack", "health", "max_health", "tier",
    "tribe", "keywords", "divine_shield", "golden",
}

_SELF_KEYS = {
    "player_id", "name", "health", "armor", "tavern_tier", "locked",
    "board", "hero", "is_bot", "is_ghost",
    "hand", "gold", "max_gold", "upgrade_cost", "shop", "frozen",
    "hero_power_uses_left",
}

_OPPONENT_KEYS = {
    "player_id", "name", "health", "armor", "tavern_tier", "locked",
    "board", "hero", "is_bot", "is_ghost",
}

_LEADERBOARD_ENTRY_KEYS = {
    "player_id", "name", "health", "armor", "is_bot", "is_ghost", "last_combat_board",
}

_STATE_MSG_KEYS = {
    "type", "round", "phase", "winner", "buy_seconds_left", "self", "opponent", "leaderboard",
}


def test_minion_snapshot_has_all_expected_keys():
    m = CARD_CATALOG["iron_automaton"].create_instance()
    assert _MINION_KEYS <= set(m.to_dict())


def test_self_snapshot_has_all_expected_keys():
    p = PlayerState(player_id="p1", name="p1")
    assert _SELF_KEYS <= set(p.to_dict(as_self=True))


def test_opponent_snapshot_excludes_private_fields():
    p = PlayerState(player_id="p1", name="p1")
    d = p.to_dict(as_self=False)
    assert _OPPONENT_KEYS <= set(d)
    assert "hand" not in d
    assert "gold" not in d
    assert "shop" not in d


def test_state_message_has_all_expected_keys():
    player = PlayerState(player_id="p1", name="p1")
    opponent = PlayerState(player_id="p2", name="p2", is_bot=True)
    match = Match(match_id="proto-test", players=[player, opponent], seed=0)
    received: list[dict] = []

    async def capture(raw: str) -> None:
        import json
        received.append(json.loads(raw))

    async def run() -> None:
        match.register_sender("p1", capture)
        await match.send_state("p1")

    asyncio.run(run())
    assert received, "no state message sent"
    msg = received[0]
    assert _STATE_MSG_KEYS <= set(msg)
    assert _SELF_KEYS <= set(msg["self"])
    assert _LEADERBOARD_ENTRY_KEYS <= set(msg["leaderboard"][0])
