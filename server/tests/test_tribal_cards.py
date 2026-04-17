import random

from src.cards.catalog import CARD_CATALOG, SHOP_CARDS
from src.combat.engine import resolve_combat
from src.match.actions import play

from .conftest import bare, card, make_player, make_pool, make_rng


TRIBAL_CARD_IDS = {
    "pack_leader",
    "mama_bear",
    "hunting_hound",
    "prowling_cat",
    "cobalt_guardian",
    "deflect-o-bot",
    "junkbot",
    "scrap_imp",
}


def test_tribal_cards_are_in_catalog_and_shop():
    shop_ids = {c.id for c in SHOP_CARDS}
    assert TRIBAL_CARD_IDS <= set(CARD_CATALOG)
    assert TRIBAL_CARD_IDS <= shop_ids


def test_pack_leader_buffs_existing_beasts_only():
    player = make_player()
    beast = card("ashen_rat")
    neutral = card("shield_bearer")
    player.board = [beast, neutral]
    player.hand = [card("pack_leader")]

    result = play(player, 0, make_pool(), make_rng())

    assert result == {"ok": True}
    assert beast.attack == CARD_CATALOG["ashen_rat"].base_attack + 1
    assert neutral.attack == CARD_CATALOG["shield_bearer"].base_attack
    assert player.board[-1].attack == CARD_CATALOG["pack_leader"].base_attack


def test_hunting_hound_combat_start_requires_three_beasts():
    hound = card("hunting_hound")
    result = resolve_combat(
        [hound, card("ashen_rat"), card("mossback_turtle")],
        [],
        random.Random(42),
        1,
        1,
    )
    survivor = next(m for m in result["surviving_a"] if m["instance_id"] == hound.instance_id)
    assert survivor["attack"] == CARD_CATALOG["hunting_hound"].base_attack + 2

    hound = card("hunting_hound")
    result = resolve_combat(
        [hound, card("ashen_rat"), card("shield_bearer")],
        [],
        random.Random(42),
        1,
        1,
    )
    survivor = next(m for m in result["surviving_a"] if m["instance_id"] == hound.instance_id)
    assert survivor["attack"] == CARD_CATALOG["hunting_hound"].base_attack


def test_cobalt_guardian_gains_divine_shield_from_mech_spawn_only():
    player = make_player()
    guardian = card("cobalt_guardian")
    player.board = [guardian]
    player.hand = [card("clockwork_squire")]

    play(player, 0, make_pool(), make_rng())

    assert guardian.divine_shield is True

    player = make_player()
    guardian = card("cobalt_guardian")
    player.board = [guardian]
    player.hand = [card("ashen_rat")]

    play(player, 0, make_pool(), make_rng())

    assert guardian.divine_shield is False


def test_deflect_o_bot_combat_start_bonus_equals_friendly_mech_count():
    bot = card("deflect-o-bot")
    result = resolve_combat(
        [bot, card("clockwork_squire"), card("bomb_bot"), card("ashen_rat")],
        [],
        random.Random(42),
        1,
        1,
    )
    survivor = next(m for m in result["surviving_a"] if m["instance_id"] == bot.instance_id)
    assert survivor["attack"] == CARD_CATALOG["deflect-o-bot"].base_attack + 3


def test_junkbot_buffs_when_friendly_mech_dies_not_enemy_mech():
    junkbot = card("junkbot")
    friendly_mech = card("bomb_bot")
    result = resolve_combat(
        [friendly_mech, junkbot],
        [bare(1, 10)],
        random.Random(42),
        1,
        1,
    )
    junkbot_buffs = [
        event for event in result["events"]
        if event["type"] == "buff" and event["target_id"] == junkbot.instance_id
    ]
    assert any(event["attack"] == 2 and event["health"] == 2 for event in junkbot_buffs)

    junkbot = card("junkbot")
    enemy_mech = card("bomb_bot")
    result = resolve_combat(
        [junkbot, bare(0, 5)],
        [enemy_mech],
        random.Random(42),
        1,
        1,
    )
    junkbot_buffs = [
        event for event in result["events"]
        if event["type"] == "buff" and event["target_id"] == junkbot.instance_id
    ]
    assert not junkbot_buffs


def test_scrap_imp_damages_hero_and_buffs_friendly_mechs_only():
    player = make_player()
    mech = card("clockwork_squire")
    neutral = card("shield_bearer")
    player.board = [mech, neutral]
    player.hand = [card("scrap_imp")]
    original_health = player.health

    play(player, 0, make_pool(), make_rng())

    scrap_imp = player.board[-1]
    assert player.health == original_health - 2
    assert mech.attack == CARD_CATALOG["clockwork_squire"].base_attack + 1
    assert mech.health == CARD_CATALOG["clockwork_squire"].base_health + 1
    assert neutral.attack == CARD_CATALOG["shield_bearer"].base_attack
    assert neutral.health == CARD_CATALOG["shield_bearer"].base_health
    assert scrap_imp.attack == CARD_CATALOG["scrap_imp"].base_attack + 1
    assert scrap_imp.health == CARD_CATALOG["scrap_imp"].base_health + 1


def test_mama_bear_buffs_beast_spawns_in_buy_phase_and_combat():
    player = make_player()
    mama = card("mama_bear")
    player.board = [mama]
    player.hand = [card("ashen_rat")]

    play(player, 0, make_pool(), make_rng())

    rat = player.board[-1]
    assert rat.attack == CARD_CATALOG["ashen_rat"].base_attack + 2
    assert rat.health == CARD_CATALOG["ashen_rat"].base_health + 2

    mama = card("mama_bear")
    result = resolve_combat(
        [bare(10, 20)],
        [card("phoenix_husk"), mama],
        random.Random(42),
        1,
        1,
    )
    phoenix_id = next(
        event["minion"]["instance_id"]
        for event in result["events"]
        if event["type"] == "summon" and event["card_id"] == "phoenix"
    )
    phoenix_buffs = [
        event for event in result["events"]
        if event["type"] == "buff" and event["target_id"] == phoenix_id
    ]
    assert any(event["attack"] == 2 and event["health"] == 2 for event in phoenix_buffs)
