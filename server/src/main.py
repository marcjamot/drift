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
                await matchmaker.queue(player_id, name, make_sender())

            elif kind == "queue_now":
                if not player_id:
                    await _send(ws, {"type": "error", "message": "login first"})
                    continue
                match = await matchmaker.skip_wait(player_id)
                if not match:
                    await _send(ws, {"type": "error", "message": "cannot skip wait now"})

            else:
                if not player_id:
                    await _send(ws, {"type": "error", "message": "login first"})
                    continue
                match = matchmaker.get_match_for_player(player_id)
                if not match:
                    await _send(ws, {"type": "error", "message": "not in a match"})
                    continue
                try:
                    result: Message = await match.handle_action(player_id, msg)
                except Exception as exc:
                    logger.exception("Unhandled error in handle_action for %s: %s", player_id, exc)
                    result = {"error": "internal server error"}
                await _send(ws, {"type": "action_result", "action": kind, **result})

    except websockets.exceptions.ConnectionClosed:
        logger.info("Connection closed: %s", player_id)
    finally:
        if player_id:
            await matchmaker.dequeue(player_id)


async def main() -> None:
    host: str = "0.0.0.0"
    port: int = 8765
    logger.info("Drift server listening on ws://%s:%d", host, port)
    async with websockets.serve(handler, host, port):
        await asyncio.Future()
