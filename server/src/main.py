import asyncio
import json
import logging
import uuid
from typing import Any, Awaitable, Callable, Dict, cast

import websockets
import websockets.exceptions

from .matchmaking import Matchmaker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

matchmaker = Matchmaker()
Message = dict[str, Any]
Sender = Callable[[str], Awaitable[None]]
_registry: Dict[str, Message] = {}


async def _send(ws: Any, msg: Message) -> None:
    await ws.send(json.dumps(msg))


async def handler(ws: Any) -> None:
    player_id: str | None = None

    def make_sender() -> Sender:
        async def _sender(data: str) -> None:
            try:
                await ws.send(data)
            except Exception:
                pass
        return _sender

    try:
        async for raw in ws:
            try:
                msg: Message = cast(Message, json.loads(raw))
            except json.JSONDecodeError:
                await _send(ws, {"type": "error", "message": "invalid JSON"})
                continue

            kind: Any = msg.get("type")

            if kind == "login":
                if player_id:
                    await _send(ws, {"type": "error", "message": "already logged in"})
                    continue
                name: str = str(msg.get("name") or "").strip()
                if not name:
                    await _send(ws, {"type": "error", "message": "name is required"})
                    continue
                player_id = str(uuid.uuid4())
                _registry[player_id] = {"name": name}
                await _send(ws, {"type": "welcome", "player_id": player_id, "name": name})
                logger.info("Login: %s (%s)", name, player_id[:8])

            elif kind == "reconnect":
                rid: str = str(msg.get("player_id") or "").strip()
                if not rid or rid not in _registry:
                    await _send(ws, {"type": "error", "message": "unknown player_id"})
                    continue
                match = matchmaker.get_match_for_player(rid)
                if not match:
                    await _send(ws, {"type": "error", "message": "no active match"})
                    continue
                player_id = rid
                match.register_sender(player_id, make_sender())
                await _send(ws, {"type": "reconnected", "player_id": player_id})
                await match.send_state(player_id)
                logger.info("Reconnected: %s", player_id[:8])

            elif kind == "queue":
                if not player_id:
                    await _send(ws, {"type": "error", "message": "login first"})
                    continue
                name: str = str(_registry[player_id]["name"])
                await _send(ws, {"type": "queued"})

                match = await matchmaker.queue(player_id, name, make_sender())

                if match:
                    for pid in match.player_order:
                        opp_id: str = match._opponent(pid)
                        await match.send_to(
                            pid,
                            {
                                "type": "match_start",
                                "match_id": match.match_id,
                                "opponent": match.players[opp_id].name,
                            },
                        )
                    asyncio.create_task(match.run())

            else:
                if not player_id:
                    await _send(ws, {"type": "error", "message": "login first"})
                    continue
                match = matchmaker.get_match_for_player(player_id)
                if not match:
                    await _send(ws, {"type": "error", "message": "not in a match"})
                    continue
                result: Message = await match.handle_action(player_id, msg)
                await _send(ws, {"type": "action_result", "action": kind, **result})

    except websockets.exceptions.ConnectionClosed:
        logger.info("Connection closed: %s", player_id)
    finally:
        if player_id:
            matchmaker.dequeue(player_id)


async def main() -> None:
    host: str = "0.0.0.0"
    port: int = 8765
    logger.info("Drift server listening on ws://%s:%d", host, port)
    async with websockets.serve(handler, host, port):
        await asyncio.Future()
