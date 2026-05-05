from .._base import Minion, MinionCard, StateContext


class StormHydra(MinionCard):
    card_id = "storm_hydra"
    card_name = "Storm Hydra"
    attack = 6
    health = 6
    tavern_tier = 4

    def on_state(self, minion: Minion, ctx: StateContext) -> None:
        ctx.emit("keyword.add", {"keyword": "cleave", "target_id": minion.instance_id},
                 {f"minion:{minion.instance_id}:cleave": True})
