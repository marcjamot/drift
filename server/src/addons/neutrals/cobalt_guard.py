from .._base import Minion, MinionCard, StateContext


class CobaltGuard(MinionCard):
    card_id = "cobalt_guard"
    card_name = "Cobalt Guard"
    attack = 3
    health = 2
    tavern_tier = 2

    def on_state(self, minion: Minion, ctx: StateContext) -> None:
        ctx.emit("keyword.add", {"keyword": "divine_shield", "target_id": minion.instance_id},
                 {f"minion:{minion.instance_id}:divine_shield": True})
