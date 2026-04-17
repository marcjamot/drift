import random

from src.cards.base import CardDef
from src.cards.catalog import CARD_CATALOG
from src.combat.engine import resolve_combat
from .conftest import bare


def test_reborn_minion_dies_and_revives_at_one_health_without_reborn():
    reborn = bare(1, 1, keywords={"reborn", "poisonous"})
    result = resolve_combat([bare(10, 10), bare(1, 1)], [reborn], random.Random(42), 1, 1)

    reborn_event = next(
        e for e in result["events"]
        if e["type"] == "reborn_trigger" and e["minion_id"] == reborn.instance_id
    )
    revived = reborn_event["minion"]
    assert revived["health"] == 1
    assert "reborn" not in revived["keywords"]
    assert "poisonous" in revived["keywords"]


def test_reborn_minion_that_dies_again_does_not_revive_twice():
    reborn = bare(0, 1, keywords={"reborn"})
    result = resolve_combat([bare(1, 10), bare(1, 10)], [reborn], random.Random(42), 1, 1)

    reborn_events = [e for e in result["events"] if e["type"] == "reborn_trigger"]
    assert len(reborn_events) == 1
    assert not result["surviving_b"]


def test_poisonous_attacker_kills_high_health_minion_with_one_damage():
    poisonous = bare(1, 10, keywords={"poisonous"})
    target = bare(0, 10)
    result = resolve_combat([poisonous, bare(1, 1)], [target], random.Random(42), 1, 1)

    deaths = {e["minion_id"] for e in result["events"] if e["type"] == "death"}
    assert target.instance_id in deaths
    assert not result["surviving_b"]


def test_hitting_poisonous_minion_does_not_destroy_attacker_by_contact():
    attacker = bare(1, 10)
    poisonous = bare(0, 10, keywords={"poisonous"})
    result = resolve_combat([attacker, bare(1, 1)], [poisonous], random.Random(42), 1, 1)

    attacker_state = next(m for m in result["surviving_a"] if m["instance_id"] == attacker.instance_id)
    assert attacker_state["health"] == 10


def test_cleave_attacker_damages_target_and_both_adjacent_minions():
    attacker = bare(3, 20, keywords={"cleave"})
    left = bare(0, 10)
    target = bare(0, 10, keywords={"taunt"})
    right = bare(0, 10)
    result = resolve_combat(
        [attacker, bare(1, 1), bare(1, 1), bare(1, 1)],
        [left, target, right],
        random.Random(42),
        1,
        1,
    )

    primary_hit = next(
        e for e in result["events"]
        if e["type"] == "damage_dealt" and e["defender_id"] == target.instance_id
    )
    splash_hits = [
        e for e in result["events"]
        if e["type"] == "cleave_splash" and e["target_id"] in {left.instance_id, right.instance_id}
    ][:2]
    assert primary_hit["damage_to_defender"] == 3
    assert primary_hit["defender_remaining_hp"] == 7
    assert {e["target_id"] for e in splash_hits} == {left.instance_id, right.instance_id}
    assert all(e["amount"] == 3 and e["remaining_health"] == 7 for e in splash_hits)


def test_cleave_with_one_defender_hits_only_that_minion():
    attacker = bare(3, 20, keywords={"cleave"})
    target = bare(0, 10)
    result = resolve_combat([attacker, bare(1, 1)], [target], random.Random(42), 1, 1)

    assert not [e for e in result["events"] if e["type"] == "cleave_splash"]
    primary_hit = next(
        e for e in result["events"]
        if e["type"] == "damage_dealt" and e["defender_id"] == target.instance_id
    )
    assert primary_hit["damage_to_defender"] == 3
    assert primary_hit["defender_remaining_hp"] == 7


def test_cleave_primary_and_adjacent_hits_each_pop_divine_shield():
    attacker = bare(3, 20, keywords={"cleave"})
    left = bare(0, 10, divine_shield=True)
    target = bare(0, 10, keywords={"taunt"}, divine_shield=True)
    right = bare(0, 10, divine_shield=True)
    result = resolve_combat(
        [attacker, bare(1, 1), bare(1, 1), bare(1, 1)],
        [left, target, right],
        random.Random(42),
        1,
        1,
    )

    primary_hit = next(
        e for e in result["events"]
        if e["type"] == "damage_dealt" and e["defender_id"] == target.instance_id
    )
    splash_hits = [
        e for e in result["events"]
        if e["type"] == "cleave_splash"
    ][:2]
    splash_by_id = {e["target_id"]: e for e in splash_hits}
    assert primary_hit["damage_to_defender"] == 0
    assert primary_hit["defender_divine_shield"] is False
    assert splash_by_id[left.instance_id]["amount"] == 0
    assert splash_by_id[left.instance_id]["remaining_divine_shield"] is False
    assert splash_by_id[right.instance_id]["amount"] == 0
    assert splash_by_id[right.instance_id]["remaining_divine_shield"] is False


def test_cleave_splash_does_not_trigger_additional_on_attack_hooks():
    calls = {"count": 0}

    def on_attack(minion, event, ctx):
        calls["count"] += 1

    CARD_CATALOG["__test_cleave_hook__"] = CardDef(
        id="__test_cleave_hook__",
        name="Hook Cleaver",
        base_attack=3,
        base_health=20,
        tier=1,
        keywords=["cleave"],
        on_attack=on_attack,
    )
    try:
        attacker = CARD_CATALOG["__test_cleave_hook__"].create_instance()
        target = bare(0, 10, keywords={"taunt"})
        result = resolve_combat(
            [attacker, bare(1, 1)],
            [bare(0, 10), target, bare(0, 10)],
            random.Random(42),
            1,
            1,
        )
    finally:
        del CARD_CATALOG["__test_cleave_hook__"]

    assert calls["count"] == len([e for e in result["events"] if e["type"] == "attack" and e["attacker_id"] == attacker.instance_id])


def test_windfury_minion_attacks_twice_before_next_minion_attacks():
    windfury = bare(1, 20, keywords={"windfury"})
    next_minion = bare(1, 20)
    result = resolve_combat([windfury, next_minion], [bare(0, 20)], random.Random(42), 1, 1)

    attacks = [e for e in result["events"] if e["type"] == "attack"]
    assert attacks[0]["attacker_id"] == windfury.instance_id
    assert attacks[1]["attacker_id"] == windfury.instance_id
    assert attacks[2]["attacker_id"] != windfury.instance_id


def test_windfury_minion_that_dies_on_first_attack_does_not_attack_again():
    windfury = bare(10, 1, keywords={"windfury"})
    result = resolve_combat([windfury, bare(1, 20)], [bare(1, 50)], random.Random(42), 1, 1)

    windfury_attacks = [
        e for e in result["events"]
        if e["type"] == "attack" and e["attacker_id"] == windfury.instance_id
    ]
    assert len(windfury_attacks) == 1
