from .._base import Minion, MinionCard, StateContext


class ShieldBearer(MinionCard):
    card_id = "shield_bearer"
    card_name = "Shield Bearer"
    attack = 1
    health = 4
    tavern_tier = 1

    def on_state(self, minion: Minion, ctx: StateContext) -> None:
        ctx.emit("keyword.add", {"keyword": "taunt", "target_id": minion.instance_id},
                 {f"minion:{minion.instance_id}:taunt": True})
