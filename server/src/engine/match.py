from __future__ import annotations

import random
from pathlib import Path
from typing import Any

from ..addons import DEFAULT_ADDONS
from ..states import BeginState, CombatState, EndState, HeroSelectState, ShopState
from .context import MatchContext, Sender
from .event_bus import EventBus
from .models import CardCatalog, CardPool, PlayerState
from .replay import ReplayLogger
from .state_machine import State, StateMachine
from .store import Store

Message = dict[str, Any]
ActionResult = dict[str, Any]


class Match:
    """Bootstrap and I/O shell. Game flow lives in StateMachine + states + MatchContext."""

    def __init__(
        self,
        match_id: str,
        players: list[PlayerState],
        seed: int | None = None,
        addon_types: list[type] | None = None,
        replay_path: Path | None = None,
    ) -> None:
        self.match_id = match_id
        self.player_order = [player.player_id for player in players]
        self.players = {player.player_id: player for player in players}
        self.seed = seed if seed is not None else hash(match_id) & 0xFFFFFFFF
        self.rng = random.Random(self.seed)

        self.catalog = CardCatalog()
        self.replay = ReplayLogger(match_id=match_id, seed=self.seed, path=replay_path)
        store = Store()
        bootstrap_pool = CardPool([], random.Random(self.seed ^ 0xDEAD))
        self.ctx = MatchContext(
            match_id=match_id,
            players=self.players,
            player_order=self.player_order,
            round=1,
            event_bus=EventBus(),
            pool=bootstrap_pool,
            catalog=self.catalog,
            rng=self.rng,
            replay=self.replay,
            store=store,
        )
        for player in self.ctx.players.values():
            player.bind(store)

        self.states: dict[str, State] = {
            "begin": BeginState(),
            "hero_select": HeroSelectState(),
            "shop": ShopState(),
            "combat": CombatState(),
            "end": EndState(),
        }
        core_states = [
            self.states["begin"],
            self.states["hero_select"],
            self.states["shop"],
            self.states["combat"],
            self.states["end"],
        ]
        self.machine = StateMachine(self.ctx, core_states)
        self._wire_transitions(self.machine)
        for addon_type in addon_types or DEFAULT_ADDONS:
            addon = addon_type()
            addon.install(self.machine, self.catalog)
        self.ctx.pool = CardPool(self.catalog.all_playable(), random.Random(self.seed ^ 0xDEAD))
        self.replay.set_metadata(
            players=[player.to_dict(as_self=True) for player in players],
            addons=[addon_type.__name__ for addon_type in addon_types or DEFAULT_ADDONS],
            cards=[card.to_dict() for card in self.catalog.all()],
        )

    def _wire_transitions(self, machine: StateMachine) -> None:
        def always(_ctx: object) -> bool:
            return True

        machine.add_transition("begin", always, "hero_select")
        machine.add_transition("hero_select", always, "shop")
        machine.add_transition("shop", lambda ctx: ctx.phase == "game_over", "end", priority=10)
        machine.add_transition("shop", always, "combat")
        machine.add_transition("combat", lambda ctx: len(ctx.alive_players()) <= 1, "end", priority=10)
        machine.add_transition("combat", always, "shop")

    @property
    def round(self) -> int:
        return self.ctx.round

    @round.setter
    def round(self, value: int) -> None:
        self.ctx.round = value

    @property
    def phase(self) -> str:
        return self.ctx.phase

    @phase.setter
    def phase(self, value: str) -> None:
        self.ctx.phase = value

    @property
    def winner(self) -> str | None:
        return self.ctx.winner

    @winner.setter
    def winner(self, value: str | None) -> None:
        self.ctx.winner = value

    @property
    def combat_pairs(self) -> dict[str, str]:
        return dict(self.ctx.combat_pairs)

    def register_sender(self, player_id: str, send_fn: Sender) -> None:
        self.ctx.register_sender(player_id, send_fn)

    def unregister_sender(self, player_id: str) -> None:
        self.ctx.unregister_sender(player_id)

    async def send_state(self, player_id: str) -> None:
        await self.ctx.send_state(player_id)

    async def send_to(self, player_id: str, msg: Message) -> None:
        await self.ctx.send_to(player_id, msg)

    async def run(self) -> None:
        try:
            await self.machine.run()
        finally:
            self.replay.flush()

    async def handle_action(self, player_id: str, action: Message) -> ActionResult:
        async with self.ctx.lock:
            kind = action.get("type")
            if kind == "concede":
                return await self._act_concede(player_id)
            if kind == "hero_pick":
                state = self.states["hero_select"]
                if not isinstance(state, HeroSelectState):
                    return {"error": "hero selection unavailable"}
                return state.pick(self.ctx, player_id, action)
            # Try addon intent handlers before falling through to state handling
            intent_result = self.ctx.dispatch_intent(player_id, action)
            if intent_result is not None:
                if intent_result.get("ok"):
                    await self.ctx.broadcast_state()
                return intent_result

            current = self.ctx.current_state
            if current is None:
                return {"error": "match not started"}
            if not hasattr(current, "handle_action"):
                return {"error": f"cannot act during {self.ctx.phase}"}
            result = await current.handle_action(player_id, action, self.ctx)
            if result.get("ok"):
                await self.ctx.broadcast_state()
                player = self.players.get(player_id)
                if player and player.pending_discover:
                    await self.ctx.send_to(player_id, {
                        "type": "discover_options",
                        "options": [m.to_dict() for m in player.pending_discover],
                    })
            return result

    async def _act_concede(self, player_id: str) -> ActionResult:
        if self.ctx.phase == "game_over":
            return {"error": "game already over"}
        player = self.players[player_id]
        player.health = 0
        player.eliminated_round = self.ctx.round
        player.ghost = True
        alive_after = sum(1 for p in self.players.values() if p.health > 0)
        player.placement = alive_after + 1
        alive_players = self.ctx.alive_players()
        if len(alive_players) <= 1:
            self.ctx.winner = alive_players[0] if alive_players else None
            if self.ctx.winner:
                self.players[self.ctx.winner].placement = 1
            self.ctx.phase = "game_over"
            self.ctx.phase_end.set()
        return {"ok": True}
