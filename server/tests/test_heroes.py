"""
Hero power tests.

Buy-phase heroes are tested through actions.py.
Combat-phase heroes are tested through resolve_combat().
Each test names one hero ability and one concrete observable effect.
"""
import random

from src.cards.catalog import CARD_CATALOG
from src.combat.engine import resolve_combat
from src.heroes.catalog import MIRA, GREYHORN, SABLE
from src.match import actions
from .conftest import bare, make_player, make_pool, make_rng


# ── Mira, the Nurturer (active_click) ────────────────────────────────────────

class TestMira:
    def test_hero_power_buffs_every_board_minion(self):
        p = make_player(gold=10)
        p.hero = MIRA
        p.hero_power_uses_left = 1

        a = CARD_CATALOG["shield_bearer"].create_instance()
        b = CARD_CATALOG["bomb_bot"].create_instance()
        p.board = [a, b]

        result = actions.use_hero_power(p, {"type": "use_hero_power"}, make_rng())

        assert result == {"ok": True}
        assert p.hero_power_uses_left == 0
        assert a.attack == CARD_CATALOG["shield_bearer"].base_attack + 1
        assert a.health == CARD_CATALOG["shield_bearer"].base_health + 1
        assert b.attack == CARD_CATALOG["bomb_bot"].base_attack + 1
        assert b.health == CARD_CATALOG["bomb_bot"].base_health + 1

    def test_hero_power_fails_when_already_used(self):
        p = make_player()
        p.hero = MIRA
        p.hero_power_uses_left = 0
        result = actions.use_hero_power(p, {"type": "use_hero_power"}, make_rng())
        assert "error" in result

    def test_hero_power_uses_reset_each_round(self):
        p = make_player()
        p.hero = MIRA
        p.hero_power_uses_left = 0
        p.start_round(2)
        assert p.hero_power_uses_left == 1

    def test_hero_power_not_granted_without_hero(self):
        p = make_player()
        p.hero = None
        result = actions.use_hero_power(p, {"type": "use_hero_power"}, make_rng())
        assert "error" in result

    def test_buffs_empty_board_is_no_op(self):
        """Using power on empty board should succeed without crashing."""
        p = make_player()
        p.hero = MIRA
        p.hero_power_uses_left = 1
        result = actions.use_hero_power(p, {"type": "use_hero_power"}, make_rng())
        assert result == {"ok": True}


# ── Greyhorn (passive on_buy) ─────────────────────────────────────────────────

class TestGreyhorn:
    def test_bought_minion_gains_two_attack(self):
        p = make_player(gold=10)
        p.hero = GREYHORN
        pool = make_pool()
        actions.refresh_shop(p, pool)

        base_attack = p.shop[0].attack
        actions.buy(p, 0, pool, make_rng())

        assert p.hand[0].attack == base_attack + 2

    def test_bought_minion_health_unchanged(self):
        p = make_player(gold=10)
        p.hero = GREYHORN
        pool = make_pool()
        actions.refresh_shop(p, pool)

        base_health = p.shop[0].health
        actions.buy(p, 0, pool, make_rng())

        assert p.hand[0].health == base_health

    def test_passive_requires_no_activation(self):
        """Greyhorn is passive — hero_power_uses_left should stay 0 each round."""
        p = make_player()
        p.hero = GREYHORN
        p.start_round(1)
        assert p.hero_power_uses_left == 0


# ── Sable, the Drifter (passive on_combat_start) ──────────────────────────────

class TestSable:
    def test_minions_gain_one_health_at_combat_start(self):
        """Sable gives +0/+1 to all friendly minions, which lets a 2/2 survive a 2/2."""
        # Without Sable: 2/2 vs 2/2 → mutual kill (draw)
        result_no_sable = resolve_combat(
            [bare(2, 2)], [bare(2, 2)], random.Random(0), 1, 1
        )
        assert result_no_sable["winner"] is None

        # With Sable on side A: 2/2 → 2/3 at combat start → survives 2 damage with 1 hp
        result_with_sable = resolve_combat(
            [bare(2, 2)], [bare(2, 2)], random.Random(0), 1, 1, hero_a=SABLE
        )
        assert result_with_sable["winner"] == 0
        assert result_with_sable["surviving_a"][0]["health"] == 1

    def test_sable_buffs_are_visible_in_events(self):
        result = resolve_combat(
            [bare(1, 1)], [bare(10, 10)], random.Random(0), 1, 1, hero_a=SABLE
        )
        buff_events = [e for e in result["events"] if e["type"] == "buff" and e["health"] > 0]
        assert buff_events, "Sable should produce buff events at combat start"

    def test_sable_does_not_buff_enemy_side(self):
        """Sable on side A should not buff side B minions."""
        enemy = bare(1, 1)
        result = resolve_combat(
            [bare(1, 10)], [enemy], random.Random(0), 1, 1, hero_a=SABLE
        )
        # Only side A minions get buffed; enemy should NOT appear in buff events
        buff_events = [e for e in result["events"] if e["type"] == "buff"]
        buffed_ids = {e["target_id"] for e in buff_events}
        assert enemy.instance_id not in buffed_ids
