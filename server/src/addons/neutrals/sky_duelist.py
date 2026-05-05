from .._base import Minion, MinionCard, StateContext


class SkyDuelist(MinionCard):
    card_id = "sky_duelist"
    card_name = "Sky Duelist"
    attack = 4
    health = 4
    tavern_tier = 3

    def on_state(self, minion: Minion, ctx: StateContext) -> None:
        ctx.emit("keyword.add", {"keyword": "windfury", "target_id": minion.instance_id},
                 {f"minion:{minion.instance_id}:windfury": True})
