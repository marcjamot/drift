from __future__ import annotations

from ..engine.context import MatchContext, StateContext
from ..engine.state_machine import State


class EndState(State):
    name = "end"
    type = "end"

    async def enter(self, ctx: MatchContext) -> None:
        ctx.phase = "game_over"
        ctx.enter_state(StateContext(type=self.type, match=ctx))
        alive = ctx.alive_players()
        if ctx.winner is None and alive:
            ctx.winner = alive[0]
        if ctx.winner:
            ctx.players[ctx.winner].placement = 1
        remaining = [p for p in ctx.players.values() if p.placement is None]
        used = {p.placement for p in ctx.players.values() if p.placement is not None}
        open_slots = [slot for slot in range(1, len(ctx.players) + 1) if slot not in used]
        for player, placement in zip(remaining, open_slots):
            player.placement = placement
        ctx.replay.update_current_snapshot(ctx)
        await ctx.notify_survivors_game_over()
        await ctx.broadcast({
            "type": "game_over",
            "winner": ctx.winner,
            "placements": {pid: p.placement for pid, p in ctx.players.items()},
        })
