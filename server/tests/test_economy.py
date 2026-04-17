"""
Buy-phase economy tests.

All tests call functions from src/match/actions.py directly — no async, no
Match object required.  Each test names exactly one rule it is verifying.
"""


from src.cards.catalog import CARD_CATALOG
from src.player.player import (
    BUY_COST,
    REFRESH_COST,
    SELL_VALUE,
    gold_for_round,
    compute_upgrade_cost,
)
from src.match import actions
from src.match.triples import discover_pick
from .conftest import make_player, make_pool, make_rng


# ── gold / upgrade-cost formulas ──────────────────────────────────────────────

class TestGoldFormulas:
    def test_gold_increases_with_round(self):
        assert gold_for_round(1) == 3
        assert gold_for_round(2) == 4
        assert gold_for_round(8) == 10

    def test_gold_caps_at_ten(self):
        assert gold_for_round(9) == 10
        assert gold_for_round(50) == 10

    def test_upgrade_cost_decreases_each_round(self):
        # tier-1 base cost is 5; after round 1 it drops by (round-1)
        assert compute_upgrade_cost(1, 1) == 5
        assert compute_upgrade_cost(1, 2) == 4
        assert compute_upgrade_cost(1, 6) == 0

    def test_upgrade_cost_floors_at_zero(self):
        assert compute_upgrade_cost(1, 100) == 0


# ── start_round state reset ───────────────────────────────────────────────────

class TestStartRound:
    def test_gold_is_refreshed(self):
        p = make_player(gold=0)
        p.start_round(3)
        assert p.gold == gold_for_round(3)

    def test_locked_is_reset(self):
        p = make_player()
        p.locked = True
        p.start_round(1)
        assert not p.locked

    def test_upgrade_cost_is_recalculated(self):
        p = make_player(tier=1)
        p.start_round(3)
        assert p.upgrade_cost == compute_upgrade_cost(1, 3)


# ── buy ───────────────────────────────────────────────────────────────────────

class TestBuy:
    def _player_with_shop(self):
        p = make_player(gold=10)
        pool = make_pool()
        actions.refresh_shop(p, pool)
        return p, pool

    def test_buy_moves_card_from_shop_to_hand(self):
        p, pool = self._player_with_shop()
        shop_card_id = p.shop[0].card_id
        actions.buy(p, 0, pool, make_rng())
        assert p.hand[0].card_id == shop_card_id
        assert p.shop[0] is None

    def test_buy_deducts_gold(self):
        p, pool = self._player_with_shop()
        gold_before = p.gold
        actions.buy(p, 0, pool, make_rng())
        assert p.gold == gold_before - BUY_COST

    def test_buy_fails_when_broke(self):
        p, pool = self._player_with_shop()
        p.gold = 0
        result = actions.buy(p, 0, pool, make_rng())
        assert "error" in result
        assert not p.hand

    def test_buy_fails_on_invalid_index(self):
        p, pool = self._player_with_shop()
        result = actions.buy(p, 99, pool, make_rng())
        assert "error" in result

    def test_buy_fails_on_none_index(self):
        p, pool = self._player_with_shop()
        result = actions.buy(p, None, pool, make_rng())
        assert "error" in result

    def test_buy_fails_on_empty_slot(self):
        p, pool = self._player_with_shop()
        # Buy it once to empty the slot
        actions.buy(p, 0, pool, make_rng())
        result = actions.buy(p, 0, pool, make_rng())
        assert "error" in result


# ── play ──────────────────────────────────────────────────────────────────────

class TestPlay:
    def test_play_moves_card_from_hand_to_board(self):
        p = make_player()
        p.hand.append(CARD_CATALOG["shield_bearer"].create_instance())
        actions.play(p, 0, make_pool(), make_rng())
        assert len(p.board) == 1
        assert not p.hand

    def test_play_fails_on_invalid_index(self):
        p = make_player()
        result = actions.play(p, 5, make_pool(), make_rng())
        assert "error" in result

    def test_play_fails_when_board_full(self):
        p = make_player()
        p.board = [CARD_CATALOG["shield_bearer"].create_instance() for _ in range(7)]
        p.hand.append(CARD_CATALOG["bomb_bot"].create_instance())
        result = actions.play(p, 0, make_pool(), make_rng())
        assert "error" in result
        assert len(p.hand) == 1  # card not lost

    def test_banner_pup_battlecry_buffs_another_minion(self):
        """on_play hook fires correctly through the actions layer."""
        p = make_player()
        target = CARD_CATALOG["shield_bearer"].create_instance()
        p.board.append(target)
        p.hand.append(CARD_CATALOG["banner_pup"].create_instance())

        attack_before = target.attack
        health_before = target.health
        actions.play(p, 0, make_pool(), make_rng())

        assert target.attack == attack_before + 1
        assert target.health == health_before + 1


# ── sell ──────────────────────────────────────────────────────────────────────

class TestSell:
    def test_sell_removes_minion_from_board(self):
        p = make_player(gold=0)
        p.board.append(CARD_CATALOG["shield_bearer"].create_instance())
        pool = make_pool()
        actions.sell(p, 0, pool, make_rng())
        assert not p.board

    def test_sell_grants_gold(self):
        p = make_player(gold=0)
        p.board.append(CARD_CATALOG["shield_bearer"].create_instance())
        pool = make_pool()
        actions.sell(p, 0, pool, make_rng())
        assert p.gold == SELL_VALUE

    def test_sell_returns_card_to_pool(self):
        p = make_player()
        pool = make_pool()
        pool_size_before = len(pool.available)
        p.board.append(CARD_CATALOG["shield_bearer"].create_instance())
        actions.sell(p, 0, pool, make_rng())
        assert len(pool.available) == pool_size_before + 1

    def test_sell_gold_capped_at_max(self):
        p = make_player(gold=10)
        p.max_gold = 10
        p.board.append(CARD_CATALOG["shield_bearer"].create_instance())
        actions.sell(p, 0, make_pool(), make_rng())
        assert p.gold == 10  # already at cap


# ── freeze ────────────────────────────────────────────────────────────────────

class TestFreeze:
    def test_freeze_toggles_frozen(self):
        p = make_player()
        assert not p.frozen
        actions.freeze(p)
        assert p.frozen
        actions.freeze(p)
        assert not p.frozen

    def test_frozen_shop_is_preserved_on_next_round(self):
        """BuyPhase.enter skips refresh_shop for frozen players."""
        p = make_player()
        pool = make_pool()
        actions.refresh_shop(p, pool)
        original_ids = [m.card_id if m else None for m in p.shop]

        actions.freeze(p)
        # Simulate what BuyPhase.enter does for frozen players
        p.start_round(2)
        if p.frozen:
            p.frozen = False
        else:
            actions.refresh_shop(p, pool)

        current_ids = [m.card_id if m else None for m in p.shop]
        assert current_ids == original_ids


# ── refresh ───────────────────────────────────────────────────────────────────

class TestRefresh:
    def test_refresh_costs_one_gold(self):
        p = make_player(gold=5)
        pool = make_pool()
        actions.refresh_shop(p, pool)
        gold_before = p.gold
        actions.refresh(p, pool)
        assert p.gold == gold_before - REFRESH_COST

    def test_refresh_fails_when_broke(self):
        p = make_player(gold=0)
        result = actions.refresh(p, make_pool())
        assert "error" in result

    def test_refresh_replaces_shop_contents(self):
        p = make_player(gold=10)
        pool = make_pool()
        actions.refresh_shop(p, pool)
        before = [m.instance_id if m else None for m in p.shop]
        actions.refresh(p, pool)
        after = [m.instance_id if m else None for m in p.shop]
        assert before != after


# ── upgrade ───────────────────────────────────────────────────────────────────

class TestUpgrade:
    def test_upgrade_increases_tavern_tier(self):
        p = make_player(gold=10)
        p.tavern_tier = 1
        p.upgrade_cost = 5
        actions.upgrade(p, round_num=1)
        assert p.tavern_tier == 2

    def test_upgrade_deducts_cost(self):
        p = make_player(gold=10)
        p.upgrade_cost = 5
        actions.upgrade(p, round_num=1)
        assert p.gold == 5

    def test_upgrade_fails_when_broke(self):
        p = make_player(gold=2)
        p.upgrade_cost = 5
        result = actions.upgrade(p, round_num=1)
        assert "error" in result
        assert p.tavern_tier == 1

    def test_upgrade_fails_at_max_tier(self):
        p = make_player(gold=10)
        p.tavern_tier = 6
        result = actions.upgrade(p, round_num=1)
        assert "error" in result


# ── reorder ───────────────────────────────────────────────────────────────────

class TestReorder:
    def test_reorder_swaps_positions(self):
        p = make_player()
        a = CARD_CATALOG["shield_bearer"].create_instance()
        b = CARD_CATALOG["bomb_bot"].create_instance()
        p.board = [a, b]
        actions.reorder(p, from_idx=0, to_idx=1)
        assert p.board[0].card_id == "bomb_bot"
        assert p.board[1].card_id == "shield_bearer"

    def test_reorder_fails_on_invalid_from(self):
        p = make_player()
        p.board = [CARD_CATALOG["shield_bearer"].create_instance()]
        result = actions.reorder(p, from_idx=5, to_idx=0)
        assert "error" in result

    def test_reorder_fails_without_indices(self):
        p = make_player()
        result = actions.reorder(p, from_idx=None, to_idx=None)
        assert "error" in result


# ── triple / discover ─────────────────────────────────────────────────────────

class TestTripleAndDiscover:
    def test_three_copies_become_golden(self):
        p = make_player(gold=10)
        pool = make_pool()
        rng = make_rng()

        for _ in range(3):
            p.hand.append(CARD_CATALOG["shield_bearer"].create_instance())

        # Playing one triggers check_triple: 2 in hand + 1 on board = 3
        actions.play(p, 0, pool, rng)

        assert any(m.golden for m in p.hand), "A golden should be in hand"
        assert not p.board, "Board copies removed by triple"
        assert p.pending_discover is not None

    def test_golden_has_doubled_stats(self):
        p = make_player(gold=10)
        pool = make_pool()
        base = CARD_CATALOG["shield_bearer"]

        for _ in range(3):
            p.hand.append(base.create_instance())

        actions.play(p, 0, pool, make_rng())
        golden = next(m for m in p.hand if m.golden)

        assert golden.attack == base.base_attack * 2
        assert golden.health == base.base_health * 2

    def test_discover_offers_three_options(self):
        p = make_player(gold=10)
        pool = make_pool()
        for _ in range(3):
            p.hand.append(CARD_CATALOG["shield_bearer"].create_instance())
        actions.play(p, 0, pool, make_rng())

        assert p.pending_discover is not None
        assert len(p.pending_discover) == 3

    def test_discover_pick_moves_chosen_to_hand(self):
        p = make_player(gold=10)
        pool = make_pool()
        for _ in range(3):
            p.hand.append(CARD_CATALOG["shield_bearer"].create_instance())
        actions.play(p, 0, pool, make_rng())

        chosen_id = p.pending_discover[1].card_id
        discover_pick(p, 1, pool, make_rng())

        assert p.pending_discover is None
        assert any(m.card_id == chosen_id for m in p.hand)

    def test_discover_returns_unchosen_to_pool(self):
        p = make_player(gold=10)
        pool = make_pool()
        for _ in range(3):
            p.hand.append(CARD_CATALOG["shield_bearer"].create_instance())
        actions.play(p, 0, pool, make_rng())

        size_before = len(pool.available)
        discover_pick(p, 0, pool, make_rng())
        # Two cards returned; one kept
        assert len(pool.available) == size_before + 2

    def test_discover_pick_fails_on_invalid_index(self):
        p = make_player(gold=10)
        pool = make_pool()
        for _ in range(3):
            p.hand.append(CARD_CATALOG["shield_bearer"].create_instance())
        actions.play(p, 0, pool, make_rng())

        result = discover_pick(p, 99, pool, make_rng())
        assert "error" in result
        assert p.pending_discover is not None  # not consumed

    def test_discover_pick_fails_without_pending(self):
        p = make_player()
        result = discover_pick(p, 0, make_pool(), make_rng())
        assert "error" in result
