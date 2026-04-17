from types import ModuleType

from ..base import CardDef, TRIBES
from .beast import ashen_rat as ashen_rat_module
from .beast import banner_pup as banner_pup_module
from .beast import hunting_hound as hunting_hound_module
from .beast import mama_bear as mama_bear_module
from .beast import mossback_turtle as mossback_turtle_module
from .beast import pack_matron as pack_matron_module
from .beast import pack_leader as pack_leader_module
from .beast import phoenix_husk as phoenix_husk_module
from .beast import prowling_cat as prowling_cat_module
from .beast import rally_hound as rally_hound_module
from .beast import rustfang_hyena as rustfang_hyena_module
from .beast import storm_hydra as storm_hydra_module
from .demon import blood_archivist as blood_archivist_module
from .demon import hex_dealer as hex_dealer_module
from .demon import imp_gang_boss as imp_gang_boss_module
from .demon import mal_ganis as mal_ganis_module
from .demon import titan_of_cinders as titan_of_cinders_module
from .dragon import chrono_dragon as chrono_dragon_module
from .dragon import razorgore as razorgore_module
from .dragon import twilight_emissary as twilight_emissary_module
from .mech import bomb_bot as bomb_bot_module
from .mech import clockwork_squire as clockwork_squire_module
from .mech import cobalt_guardian as cobalt_guardian_module
from .mech import deflect_o_bot as deflect_o_bot_module
from .mech import iron_automaton as iron_automaton_module
from .mech import junkbot as junkbot_module
from .mech import king_of_rust as king_of_rust_module
from .mech import scrap_imp as scrap_imp_module
from .mech import soul_foundry as soul_foundry_module
from .mech import void_engine as void_engine_module
from .murloc import megasaur as megasaur_module
from .murloc import murloc_tidecaller as murloc_tidecaller_module
from .neutral import apex_mimic as apex_mimic_module
from .neutral import mirror_assassin as mirror_assassin_module
from .neutral import shield_bearer as shield_bearer_module
from .neutral import siege_golem as siege_golem_module
from .neutral import static_idol as static_idol_module
from .neutral import stone_golem as stone_golem_module
from .neutral import tunnel_bruiser as tunnel_bruiser_module
from .pirate import goldgrub_baron as goldgrub_baron_module
from .pirate import hoggar as hoggar_module
from .pirate import scallywag as scallywag_module
from .pirate import sky_duelist as sky_duelist_module
from .pirate import tavern_troublemaker as tavern_troublemaker_module
from .undead import frost_herald as frost_herald_module
from .undead import grave_picker as grave_picker_module
from .undead import lantern_sprite as lantern_sprite_module
from .undead import soul_collector as soul_collector_module


def _card(module: ModuleType) -> CardDef:
    tribe = module.__name__.split(".")[-2]
    if tribe not in TRIBES:
        raise ValueError(f"Invalid card tribe folder: {tribe}")
    module.CARD.tribe = tribe
    return module.CARD


stone_golem = _card(stone_golem_module)
shield_bearer = _card(shield_bearer_module)
clockwork_squire = _card(clockwork_squire_module)
hunting_hound = _card(hunting_hound_module)
ashen_rat = _card(ashen_rat_module)
tavern_troublemaker = _card(tavern_troublemaker_module)
murloc_tidecaller = _card(murloc_tidecaller_module)
scallywag = _card(scallywag_module)
mossback_turtle = _card(mossback_turtle_module)
bomb_bot = _card(bomb_bot_module)
banner_pup = _card(banner_pup_module)
pack_leader = _card(pack_leader_module)
scrap_imp = _card(scrap_imp_module)
grave_picker = _card(grave_picker_module)
rustfang_hyena = _card(rustfang_hyena_module)
lantern_sprite = _card(lantern_sprite_module)
tunnel_bruiser = _card(tunnel_bruiser_module)
rally_hound = _card(rally_hound_module)
iron_automaton = _card(iron_automaton_module)
soul_collector = _card(soul_collector_module)
static_idol = _card(static_idol_module)
cobalt_guardian = _card(cobalt_guardian_module)
deflect_o_bot = _card(deflect_o_bot_module)
prowling_cat = _card(prowling_cat_module)
pack_matron = _card(pack_matron_module)
sky_duelist = _card(sky_duelist_module)
siege_golem = _card(siege_golem_module)
blood_archivist = _card(blood_archivist_module)
imp_gang_boss = _card(imp_gang_boss_module)
twilight_emissary = _card(twilight_emissary_module)
hex_dealer = _card(hex_dealer_module)
razorgore = _card(razorgore_module)
frost_herald = _card(frost_herald_module)
void_engine = _card(void_engine_module)
goldgrub_baron = _card(goldgrub_baron_module)
storm_hydra = _card(storm_hydra_module)
phoenix_husk = _card(phoenix_husk_module)
mirror_assassin = _card(mirror_assassin_module)
titan_of_cinders = _card(titan_of_cinders_module)
chrono_dragon = _card(chrono_dragon_module)
junkbot = _card(junkbot_module)
mama_bear = _card(mama_bear_module)
mal_ganis = _card(mal_ganis_module)
megasaur = _card(megasaur_module)
soul_foundry = _card(soul_foundry_module)
king_of_rust = _card(king_of_rust_module)
hoggar = _card(hoggar_module)
apex_mimic = _card(apex_mimic_module)

BASIC_CARDS = [
    stone_golem,
    shield_bearer,
    clockwork_squire,
    hunting_hound,
    ashen_rat,
    tavern_troublemaker,
    murloc_tidecaller,
    scallywag,
    mossback_turtle,
    bomb_bot,
    banner_pup,
    pack_leader,
    scrap_imp,
    grave_picker,
    rustfang_hyena,
    lantern_sprite,
    tunnel_bruiser,
    rally_hound,
    iron_automaton,
    soul_collector,
    static_idol,
    cobalt_guardian,
    deflect_o_bot,
    prowling_cat,
    pack_matron,
    sky_duelist,
    siege_golem,
    blood_archivist,
    imp_gang_boss,
    twilight_emissary,
    hex_dealer,
    razorgore,
    frost_herald,
    void_engine,
    goldgrub_baron,
    storm_hydra,
    phoenix_husk,
    mirror_assassin,
    titan_of_cinders,
    chrono_dragon,
    junkbot,
    mama_bear,
    mal_ganis,
    megasaur,
    soul_foundry,
    king_of_rust,
    hoggar,
    apex_mimic,
]
