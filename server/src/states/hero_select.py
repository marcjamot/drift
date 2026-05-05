from __future__ import annotations

import asyncio
from typing import Any

from ..engine.context import MatchContext, StateContext
from ..engine.state_machine import State

HERO_SELECTION_TIMEOUT = 30.0
HERO_OPTIONS_COUNT = 3


class HeroSelectState(State):
    name = "hero_select"
    type = "hero_select"
    deadline_seconds = HERO_SELECTION_TIMEOUT
    duration = HERO_SELECTION_TIMEOUT

    async def enter(self, ctx: MatchContext) -> None:
        ctx.phase = self.type
        ctx.enter_state(StateContext(type=self.type, match=ctx))
        self._deal_options(ctx)
        ctx.replay.update_current_snapshot(ctx)
        addon_ids = [a.id for a in ctx.addons if a.id]
        if not ctx.catalog.all_heroes():
            await ctx.broadcast({"type": "match_start", "match_id": ctx.match_id, "addon_ids": addon_ids})
            return
        ctx.hero_picks_remaining = set(ctx.human_players())
        ctx.hero_selection_done.clear()

        for pid in ctx.hero_picks_remaining:
            await ctx.send_to(pid, {
                "type": "hero_options",
                "deadline": ctx.current_deadline,
                "options": [hero.to_dict() for hero in ctx.hero_options[pid]],
            })

        if ctx.hero_picks_remaining:
            try:
                await asyncio.wait_for(ctx.hero_selection_done.wait(), timeout=self.deadline_seconds)
            except asyncio.TimeoutError:
                for pid in list(ctx.hero_picks_remaining):
                    ctx.players[pid].set_hero(ctx.hero_options[pid][0])
                    ctx.emit("hero_select.pick", {
                        "player_id": pid,
                        "hero_id": ctx.hero_options[pid][0].id,
                        "timeout": True,
                    })
                ctx.hero_picks_remaining.clear()

        await ctx.broadcast({"type": "match_start", "match_id": ctx.match_id, "addon_ids": addon_ids})

    def _deal_options(self, ctx: MatchContext) -> None:
        heroes = ctx.catalog.all_heroes()
        if not heroes:
            return
        ctx.hero_options = {}
        for pid in ctx.player_order:
            player = ctx.players[pid]
            if player.is_bot:
                player.set_hero(ctx.rng.choice(heroes))
            else:
                count = min(HERO_OPTIONS_COUNT, len(heroes))
                ctx.hero_options[pid] = ctx.rng.sample(heroes, count)

    def pick(self, ctx: MatchContext, player_id: str, action: dict[str, Any]) -> dict[str, Any]:
        if player_id not in ctx.hero_picks_remaining:
            return {"error": "hero already chosen"}
        options = ctx.hero_options.get(player_id, [])
        idx = action.get("index")
        if idx is None or not (0 <= idx < len(options)):
            return {"error": "invalid hero index"}
        ctx.players[player_id].set_hero(options[idx])
        ctx.emit("hero_select.pick", {
            "player_id": player_id,
            "hero_id": options[idx].id,
        })
        ctx.hero_picks_remaining.discard(player_id)
        if not ctx.hero_picks_remaining:
            ctx.hero_selection_done.set()
        return {"ok": True}
