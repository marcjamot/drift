from __future__ import annotations

from ..engine.context import CombatStateContext, MatchContext
from ..engine.events import AttackPayload, DamagePayload, DeathPayload, KillPayload, TargetPayload
from ..engine.models import Minion
from ..engine.state_machine import State

MAX_COMBAT_STEPS = 100


class CombatState(State):
    name = "combat"
    type = "combat"

    async def enter(self, ctx: MatchContext) -> None:
        ctx.phase = self.type
        ctx.enter_state(CombatStateContext(match=ctx))
        pairs = self._pair_players(ctx)
        ctx.combat_pairs = {}
        for player_id, opponent_id in pairs:
            ctx.combat_pairs[player_id] = opponent_id
            ctx.combat_pairs[opponent_id] = player_id
        ctx.replay.update_current_snapshot(ctx)
        await ctx.broadcast({"type": "combat_start", "round": ctx.round})

        newly_dead: list[str] = []
        for player_a, player_b in pairs:
            await self._resolve_pair(ctx, player_a, player_b, newly_dead)

        if newly_dead:
            ctx.assign_placements_for_dead(newly_dead)
            await ctx.notify_eliminations()

        alive = ctx.alive_players()
        if len(alive) <= 1:
            ctx.winner = alive[0] if alive else None
            if ctx.winner:
                ctx.players[ctx.winner].placement = 1
            ctx.phase = "game_over"

        await ctx.broadcast_state()

    def _pair_players(self, ctx: MatchContext) -> list[tuple[str, str]]:
        alive = ctx.alive_players()
        ghosts = ctx.ghost_players()
        shuffled = list(alive)
        ctx.rng.shuffle(shuffled)
        if len(shuffled) % 2 == 1 and ghosts:
            shuffled.append(ghosts[0])
        pairs = []
        for index in range(0, len(shuffled) - 1, 2):
            pairs.append((shuffled[index], shuffled[index + 1]))
        return pairs

    async def _resolve_pair(
        self,
        ctx: MatchContext,
        player_a: str,
        player_b: str,
        newly_dead: list[str],
    ) -> None:
        a = ctx.players[player_a]
        b = ctx.players[player_b]
        board_a = [m.copy() for m in a.board]
        board_b = [m.copy() for m in b.board]
        contexts = [
            CombatStateContext(match=ctx, friendly_board=board_a, enemy_board=board_b),
            CombatStateContext(match=ctx, friendly_board=board_b, enemy_board=board_a),
        ]
        self._init_pair(ctx, a, board_a, contexts[0])
        self._init_pair(ctx, b, board_b, contexts[1])
        ctx.state_context = contexts[0]
        result = self._resolve_combat(ctx, board_a, board_b, a.tavern_tier, b.tavern_tier)
        ctx.event_bus.clear_temporary()

        if result["winner"] == 0:
            ctx.apply_player_damage(b, result["damage"])
        elif result["winner"] == 1:
            ctx.apply_player_damage(a, result["damage"])

        a.last_combat_board = result["surviving_a"]
        b.last_combat_board = result["surviving_b"]
        for player in (a, b):
            if player.health <= 0 and not player.ghost and player.player_id not in newly_dead:
                newly_dead.append(player.player_id)

        payload = {
            "round": ctx.round,
            "players": [player_a, player_b],
            "initial_a": [m.to_dict(self._minion_extras(ctx, m)) for m in a.board],
            "initial_b": [m.to_dict(self._minion_extras(ctx, m)) for m in b.board],
            "events": result["events"],
            "surviving_a": result["surviving_a"],
            "surviving_b": result["surviving_b"],
        }
        await ctx.send_to(player_a, {"type": "combat_log", **payload, "is_ghost": b.ghost})
        await ctx.send_to(player_b, {"type": "combat_log", **payload, "is_ghost": a.ghost})

    def _init_pair(self, ctx: MatchContext, player, board: list[Minion], state_ctx: CombatStateContext) -> None:
        if player.hero:
            player.hero.on_state(ctx._hero_subject(player), state_ctx)
        for minion in board:
            card = ctx.catalog.maybe_get(minion.card_id)
            if card:
                card.on_state(minion, state_ctx)

    def _deal_damage(self, ctx: MatchContext, source: Minion, subject: Minion, amount: int) -> int:
        payload = DamagePayload(source=source, subject=subject, amount=amount, original_amount=amount)
        ctx.event_bus.emit(payload)
        actual = max(0, payload.amount)
        new_health = subject.health - actual if actual else subject.health
        ctx.emit(
            "entity.damage",
            {"source_id": source.instance_id, "target_id": subject.instance_id,
             "amount": actual, "original_amount": payload.original_amount},
            {f"minion:{subject.instance_id}:health": new_health} if actual else {},
        )
        return actual

    def _resolve_combat(
        self,
        ctx: MatchContext,
        board_a: list[Minion],
        board_b: list[Minion],
        tavern_tier_a: int,
        tavern_tier_b: int,
    ) -> dict:
        boards = [board_a, board_b]
        events: list[dict] = []
        ctx.event_bus.emit({"event": "combat_start", "boards": boards})
        current = 0 if len(board_a) >= len(board_b) else 1
        if len(board_a) == len(board_b):
            current = ctx.rng.choice([0, 1])
        next_indexes = [0, 0]

        step = 0
        while True:
            if step >= MAX_COMBAT_STEPS:
                step_payload = {
                    "event": "combat_step_limit",
                    "type": "combat_step_limit",
                    "step_limit": MAX_COMBAT_STEPS,
                    "surviving_a": [m.to_dict() for m in boards[0] if m.is_alive()],
                    "surviving_b": [m.to_dict() for m in boards[1] if m.is_alive()],
                }
                ctx.event_bus.emit(step_payload)
                events.append(step_payload)
                break
            step += 1

            if not boards[0] or not boards[1]:
                break
            attacker, attacker_index = self._next_attacker(boards[current], next_indexes[current])
            defender = self._choose_target(boards[1 - current], ctx)
            if attacker is None or defender is None:
                break

            target_payload = TargetPayload(
                actor=attacker, actor_side=current,
                target=defender, target_side=1 - current,
                source_board=boards[current], target_board=boards[1 - current],
                rng=ctx.rng,
            )
            ctx.event_bus.emit(target_payload)
            defender = target_payload.target

            ctx.emit("entity.attack", {
                "attacker_id": attacker.instance_id,
                "attacker_name": attacker.name,
                "defender_id": defender.instance_id,
                "defender_name": defender.name,
            })
            events.append({
                "type": "attack",
                "attacker_id": attacker.instance_id,
                "attacker_name": attacker.name,
                "defender_id": defender.instance_id,
                "defender_name": defender.name,
            })

            damage_to_attacker = self._deal_damage(ctx, defender, attacker, defender.attack)
            damage_to_defender = self._deal_damage(ctx, attacker, defender, attacker.attack)
            attack_payload = AttackPayload(
                actor=attacker, actor_side=current,
                target=defender, target_side=1 - current,
                source_board=boards[current], target_board=boards[1 - current],
                deal_damage=lambda *, source, subject: self._deal_damage(ctx, source, subject, source.attack),
            )
            ctx.event_bus.emit(attack_payload)
            if damage_to_attacker and not attacker.is_alive():
                ctx.event_bus.emit(KillPayload(actor=defender, target=attacker,
                                               actor_side=1 - current, target_side=current))
            if damage_to_defender and not defender.is_alive():
                ctx.event_bus.emit(KillPayload(actor=attacker, target=defender,
                                               actor_side=current, target_side=1 - current))
            events.append({
                "type": "damage",
                "attacker_id": attacker.instance_id,
                "attacker_remaining_hp": attacker.health,
                "damage_to_attacker": damage_to_attacker,
                "defender_id": defender.instance_id,
                "defender_remaining_hp": defender.health,
                "damage_to_defender": damage_to_defender,
            })

            self._resolve_deaths(ctx, boards, events)

            next_indexes[current] = self._advance_index(boards[current], attacker_index, attacker.instance_id)
            if attack_payload.repeat_actor and any(m.instance_id == attacker.instance_id and m.is_alive() for m in boards[current]):
                continue
            current = 1 - current

        alive_a = [m for m in boards[0] if m.is_alive()]
        alive_b = [m for m in boards[1] if m.is_alive()]
        if alive_a and not alive_b:
            winner = 0
            damage = tavern_tier_a + sum(m.tier for m in alive_a)
        elif alive_b and not alive_a:
            winner = 1
            damage = tavern_tier_b + sum(m.tier for m in alive_b)
        else:
            winner = None
            damage = 0
        return {
            "winner": winner,
            "damage": damage,
            "events": events,
            "surviving_a": [m.to_dict(self._minion_extras(ctx, m)) for m in alive_a],
            "surviving_b": [m.to_dict(self._minion_extras(ctx, m)) for m in alive_b],
        }

    def _resolve_deaths(self, ctx: MatchContext, boards: list[list[Minion]], events: list[dict]) -> None:
        while True:
            resolved = False
            for side, board in enumerate(boards):
                for minion in list(board):
                    if minion.is_alive():
                        continue
                    position = board.index(minion)
                    board.remove(minion)
                    death_payload = DeathPayload(
                        subject=minion, subject_side=side, board=board, position=position,
                    )
                    ctx.event_bus.emit(death_payload)
                    ctx.emit("entity.kill", {"target_id": minion.instance_id, "target_name": minion.name})
                    events.append({"type": "death", "minion_id": minion.instance_id, "player_idx": side})
                    for spawned in death_payload.spawned:
                        spawn_position = board.index(spawned) if spawned in board else len(board)
                        ctx.emit("entity.spawn", {
                            "owner_id": None, "position": spawn_position,
                            "minion_id": spawned.instance_id,
                        })
                        events.append({
                            "type": "spawn",
                            "minion_id": spawned.instance_id,
                            "player_idx": side,
                            "minion": spawned.to_dict(self._minion_extras(ctx, spawned)),
                        })
                    resolved = True
            if not resolved:
                break

    def _minion_extras(self, ctx: MatchContext, minion: Minion) -> dict:
        _top_level = frozenset({"attack", "health", "golden"})
        return {k: v for k, v in ctx.store.prefix(f"minion:{minion.instance_id}:").items()
                if k not in _top_level}

    def _choose_target(self, board: list[Minion], ctx: MatchContext) -> Minion | None:
        alive = [m for m in board if m.is_alive()]
        return ctx.rng.choice(alive) if alive else None

    def _next_attacker(self, board: list[Minion], start_index: int) -> tuple[Minion | None, int]:
        if not board:
            return None, 0
        for offset in range(len(board)):
            index = (start_index + offset) % len(board)
            if board[index].is_alive():
                return board[index], index
        return None, 0

    def _advance_index(self, board: list[Minion], previous_index: int, attacker_id: str) -> int:
        if not board:
            return 0
        for index, minion in enumerate(board):
            if minion.instance_id == attacker_id:
                return (index + 1) % len(board)
        return previous_index % len(board)
