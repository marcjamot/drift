from .._base import Minion, MinionCard, StateContext


class PhoenixHusk(MinionCard):
    card_id = "phoenix_husk"
    card_name = "Phoenix Husk"
    attack = 5
    health = 3
    tavern_tier = 4

    def on_state(self, minion: Minion, ctx: StateContext) -> None:
        ctx.emit("keyword.add", {"keyword": "reborn", "target_id": minion.instance_id},
                 {f"minion:{minion.instance_id}:reborn": True})
