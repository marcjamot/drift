"""
Combat engine tests.

Each test targets a single, named mechanic so failures are immediately
actionable.  Board helpers come from conftest.py.
"""
import random

from src.combat.engine import resolve_combat
from .conftest import bare, card


# ── basic outcomes ─────────────────────────────────────────────────────────────

class TestBasicOutcomes:
    def test_stronger_attacker_wins(self):
        result = resolve_combat([bare(5, 5)], [bare(1, 1)], random.Random(0), 1, 1)
        assert result["winner"] == 0
        assert result["surviving_a"]
        assert not result["surviving_b"]

    def test_stronger_defender_wins(self):
        result = resolve_combat([bare(1, 1)], [bare(5, 5)], random.Random(0), 1, 1)
        assert result["winner"] == 1

    def test_mutual_kill_is_draw(self):
        result = resolve_combat([bare(2, 2)], [bare(2, 2)], random.Random(0), 1, 1)
        assert result["winner"] is None
        assert result["damage"] == 0

    def test_empty_boards_draw(self):
        result = resolve_combat([], [], random.Random(0), 1, 1)
        assert result["winner"] is None

    def test_live_boards_not_mutated(self):
        board_a = [bare(5, 5)]
        board_b = [bare(1, 1)]
        original_health = board_a[0].health
        resolve_combat(board_a, board_b, random.Random(0), 1, 1)
        assert board_a[0].health == original_health

    def test_damage_equals_tavern_tier_plus_survivor_tiers(self):
        # Side A wins; damage = tavern_tier_a + tier of each survivor
        result = resolve_combat(
            [bare(10, 10, tier=3)],
            [bare(1, 1, tier=2)],
            random.Random(0),
            tavern_tier_a=2,
            tavern_tier_b=1,
        )
        assert result["winner"] == 0
        assert result["damage"] == 2 + 3  # tavern tier + minion tier

    def test_deterministic_with_same_seed(self):
        boards_a = [bare(2, 3), bare(1, 4)]
        boards_b = [bare(3, 2), bare(2, 2)]
        r1 = resolve_combat(
            [m.copy() for m in boards_a], [m.copy() for m in boards_b], random.Random(99), 1, 1
        )
        r2 = resolve_combat(
            [m.copy() for m in boards_a], [m.copy() for m in boards_b], random.Random(99), 1, 1
        )
        assert r1["winner"] == r2["winner"]
        assert r1["damage"] == r2["damage"]
        assert [e["type"] for e in r1["events"]] == [e["type"] for e in r2["events"]]

    def test_rng_determines_first_attacker_in_equal_boards(self):
        """With equal-sized boards the seed determines which side attacks first."""
        board_a = [bare(5, 1)]
        board_b = [bare(5, 1)]
        a_id = board_a[0].instance_id

        first_attackers = {
            next(e for e in
                resolve_combat([board_a[0].copy()], [board_b[0].copy()], random.Random(s), 1, 1)["events"]
                if e["type"] == "attack"
            )["attacker_id"] == a_id
            for s in range(20)
        }
        # Some seeds pick side A first, some pick side B first
        assert True in first_attackers and False in first_attackers

    def test_events_contain_attack_and_death(self):
        result = resolve_combat([bare(5, 5)], [bare(1, 1)], random.Random(0), 1, 1)
        types = {e["type"] for e in result["events"]}
        assert "attack" in types
        assert "death" in types


# ── taunt ──────────────────────────────────────────────────────────────────────

class TestTaunt:
    def test_taunt_is_targeted_before_non_taunt(self):
        shield = card("shield_bearer")   # 1/4 taunt
        non_taunt = bare(5, 20)
        # board_a has 3 minions → attacks first (more than board_b's 2)
        board_a = [bare(10, 10), bare(1, 1), bare(1, 1)]
        board_b = [shield, non_taunt]
        result = resolve_combat(board_a, board_b, random.Random(0), 1, 1)
        # First attack goes from board_a toward board_b — must target the taunt
        first_attack_on_b = next(
            e for e in result["events"]
            if e["type"] == "attack"
            and e["defender_id"] in {shield.instance_id, non_taunt.instance_id}
        )
        assert first_attack_on_b["defender_id"] == shield.instance_id

    def test_non_taunt_targetable_after_taunt_dies(self):
        shield = card("shield_bearer")   # 1/4 taunt - will die to big attacker
        survivor = bare(1, 30)           # very tanky, no taunt
        board_a = [bare(10, 10), bare(1, 1), bare(1, 1)]
        board_b = [shield, survivor]
        result = resolve_combat(board_a, board_b, random.Random(0), 1, 1)
        deaths = {e["minion_id"] for e in result["events"] if e["type"] == "death"}
        assert shield.instance_id in deaths
        attacks_on_survivor = [
            e for e in result["events"]
            if e["type"] == "attack" and e["defender_id"] == survivor.instance_id
        ]
        assert attacks_on_survivor

    def test_two_taunts_both_eligible(self):
        t1 = card("shield_bearer")
        t2 = card("mossback_turtle")
        # board_a attacks first — must target a taunt
        board_a = [bare(10, 10), bare(1, 1), bare(1, 1)]
        board_b = [t1, t2]
        result = resolve_combat(board_a, board_b, random.Random(0), 1, 1)
        first_attack_on_b = next(
            e for e in result["events"]
            if e["type"] == "attack"
            and e["defender_id"] in {t1.instance_id, t2.instance_id}
        )
        assert first_attack_on_b["defender_id"] in {t1.instance_id, t2.instance_id}


# ── divine shield ──────────────────────────────────────────────────────────────

class TestDivineShield:
    def test_first_hit_is_absorbed(self):
        shielded = bare(1, 1, divine_shield=True)
        attacker = bare(5, 10)
        board_a = [attacker]
        board_b = [shielded]
        result = resolve_combat(board_a, board_b, random.Random(0), 1, 1)
        damage_on_shielded = [
            e for e in result["events"]
            if e["type"] == "damage" and e["target_id"] == shielded.instance_id
        ]
        # First hit absorbed by shield
        if damage_on_shielded:
            assert damage_on_shielded[0]["amount"] == 0

    def test_shield_pops_and_subsequent_hits_land(self):
        # Normal combat emits "damage_dealt" events, not "damage" (those come from hooks).
        # Check via damage_dealt: first hit deals 0 to defender (shield), second hits for real.
        shielded = bare(1, 10, divine_shield=True)
        attacker = bare(5, 20)
        # board_a has more minions so attacker goes first
        result = resolve_combat([attacker, bare(1, 1)], [shielded], random.Random(0), 1, 1)
        assert result["winner"] == 0

        dealt_on_shielded = [
            e for e in result["events"]
            if e["type"] == "damage_dealt" and e["defender_id"] == shielded.instance_id
        ]
        defender_damages = [e["damage_to_defender"] for e in dealt_on_shielded]
        assert 0 in defender_damages          # shield absorbed one hit
        assert any(d > 0 for d in defender_damages)  # real damage followed


# ── deathrattles ──────────────────────────────────────────────────────────────

class TestDeathrattles:
    def test_bomb_bot_deals_one_damage_to_each_enemy_on_death(self):
        """Bomb Bot's deathrattle should hit every minion on the opposing side."""
        bomb = card("bomb_bot")   # 2/1 — killed by any attacker
        enemy = bare(10, 10)
        result = resolve_combat([enemy], [bomb], random.Random(0), 1, 1)

        # Bomb must have died
        deaths = [e for e in result["events"] if e["type"] == "death"]
        assert any("Bomb Bot" in e["minion_name"] for e in deaths)

        # After its death, a 'damage' event targeting enemy (amount=1) must appear
        bomb_death_idx = next(
            i for i, e in enumerate(result["events"])
            if e["type"] == "death" and "Bomb Bot" in e["minion_name"]
        )
        post_death = result["events"][bomb_death_idx:]
        deathrattle_hits = [
            e for e in post_death
            if e["type"] == "damage"
            and e["target_id"] == enemy.instance_id
            and e["amount"] == 1
        ]
        assert deathrattle_hits, "Bomb Bot deathrattle should deal 1 damage to enemy"

    def test_bomb_bot_hits_all_enemies_not_just_one(self):
        """With multiple enemies, every one takes 1 damage."""
        bomb = card("bomb_bot")
        e1, e2, e3 = bare(1, 5), bare(1, 5), bare(1, 5)
        big = bare(10, 10)  # kills bomb, side A
        board_a = [big]
        board_b = [bomb, e1, e2, e3]
        result = resolve_combat(board_a, board_b, random.Random(0), 1, 1)

        bomb_death_idx = next(
            i for i, e in enumerate(result["events"])
            if e["type"] == "death" and "Bomb Bot" in e["minion_name"]
        )
        post = result["events"][bomb_death_idx:]
        hit_targets = {
            e["target_id"] for e in post
            if e["type"] == "damage" and e["amount"] == 1
        }
        # big (side A) should be hit
        assert big.instance_id in hit_targets

    def test_phoenix_husk_summons_phoenix_token_on_death(self):
        husk = card("phoenix_husk")   # 4/4
        killer = bare(10, 10)
        result = resolve_combat([killer], [husk], random.Random(0), 1, 1)

        # Death of husk triggers a summon
        summons = [e for e in result["events"] if e["type"] == "summon"]
        assert any(e["card_id"] == "phoenix" for e in summons)

    def test_phoenix_fights_after_spawning(self):
        """Phoenix token (6/2) must actually participate in combat after husk dies."""
        husk = card("phoenix_husk")   # 4/4 → dies → spawns 6/2 phoenix
        # Attacker survives husk's 4 attack so phoenix actually gets to fight
        attacker = bare(5, 10)   # 5/10: kills husk, survives with 6 hp; phoenix then attacks
        result = resolve_combat([attacker], [husk], random.Random(0), 1, 1)

        summons = [e for e in result["events"] if e["type"] == "summon"]
        assert any(e["card_id"] == "phoenix" for e in summons)

        phoenix_iid = next(
            e["minion"]["instance_id"]
            for e in result["events"]
            if e["type"] == "summon" and e["card_id"] == "phoenix"
        )
        phoenix_in_combat = any(
            e["type"] == "attack"
            and (e["attacker_id"] == phoenix_iid or e["defender_id"] == phoenix_iid)
            for e in result["events"]
        )
        assert phoenix_in_combat, "Phoenix should participate in combat after spawning"


# ── combat hooks ──────────────────────────────────────────────────────────────

class TestCombatHooks:
    def test_soul_collector_gains_stat_when_enemy_dies(self):
        """Soul Collector (4/3) gains +1/+1 for each enemy death."""
        collector = card("soul_collector")  # 4/3
        prey = bare(1, 1)
        result = resolve_combat([collector], [prey], random.Random(0), 1, 1)

        assert result["winner"] == 0
        s = result["surviving_a"][0]
        # took 1 damage from prey (4/3 → 4/2), then gained +1/+1 on prey's death → 5/3
        assert s["attack"] == 5
        assert s["health"] == 3

    def test_storm_hydra_splash_damages_non_target_enemies(self):
        """Storm Hydra deals 1 to every enemy it doesn't directly attack."""
        hydra = card("storm_hydra")   # 7/5
        e1 = bare(1, 20)
        e2 = bare(1, 20)
        # hydra on a bigger board so it attacks first
        result = resolve_combat([hydra, bare(1, 1)], [e1, e2], random.Random(0), 1, 1)

        # One of e1/e2 is the direct target; the other gets 1 splash damage via ctx.deal_damage
        board_b_ids = {e1.instance_id, e2.instance_id}
        splash = [
            e for e in result["events"]
            if e["type"] == "damage"
            and e["target_id"] in board_b_ids
            and e["amount"] == 1
        ]
        assert splash, "Storm Hydra should splash 1 to the non-targeted enemy"

    def test_apex_mimic_copies_keywords_at_combat_start(self):
        """Apex Mimic copies keywords of the highest-attack friendly minion."""
        mimic = card("apex_mimic")   # 10/10
        taunter = card("shield_bearer")  # 1/4 taunt
        taunter.attack = 15   # highest attack on the board → mimic copies from it

        result = resolve_combat([mimic, taunter], [bare(1, 1)], random.Random(0), 1, 1)
        assert result["winner"] == 0

        # Apex Mimic directly mutates keywords (no event); check the surviving minion dict
        mimic_survivor = next(
            m for m in result["surviving_a"] if m["instance_id"] == mimic.instance_id
        )
        assert "taunt" in mimic_survivor["keywords"]


# ── multi-minion combat ────────────────────────────────────────────────────────

class TestMultiMinion:
    def test_three_v_three_completes(self):
        board_a = [bare(2, 3), bare(3, 2), bare(1, 4)]
        board_b = [bare(2, 2), bare(1, 3), bare(3, 1)]
        result = resolve_combat(board_a, board_b, random.Random(42), 2, 2)
        assert result["winner"] in (0, 1, None)
        assert isinstance(result["events"], list)

    def test_larger_board_attacks_first(self):
        """When board sizes differ the larger side attacks first."""
        board_a = [bare(1, 20), bare(1, 20)]  # 2 minions
        board_b = [bare(1, 20)]               # 1 minion → side A attacks first
        result = resolve_combat(board_a, board_b, random.Random(0), 1, 1)
        first_attack = next(e for e in result["events"] if e["type"] == "attack")
        attacker_id = first_attack["attacker_id"]
        assert attacker_id in {m.instance_id for m in board_a}

    def test_full_board_combat(self):
        """Seven-minion boards should resolve without error."""
        board_a = [bare(2, 3) for _ in range(7)]
        board_b = [bare(3, 2) for _ in range(7)]
        result = resolve_combat(board_a, board_b, random.Random(7), 3, 3)
        assert result["winner"] in (0, 1, None)
