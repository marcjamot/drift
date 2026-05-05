from .._base import Minion, MinionCard, StateContext


class MirrorAssassin(MinionCard):
    card_id = "mirror_assassin"
    card_name = "Mirror Assassin"
    attack = 5
    health = 3
    tavern_tier = 5

    def on_state(self, minion: Minion, ctx: StateContext) -> None:
        ctx.emit("keyword.add", {"keyword": "poisonous", "target_id": minion.instance_id},
                 {f"minion:{minion.instance_id}:poisonous": True})
