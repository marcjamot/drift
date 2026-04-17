export type HeroPowerType =
	| "passive"
	| "active_click"
	| "active_target_shop"
	| "active_target_hand";

export interface HeroSnapshot {
	id: string;
	name: string;
	description: string;
	power_type: HeroPowerType;
}

export interface MinionSnapshot {
	instance_id: string;
	card_id: string;
	name: string;
	description: string;
	attack: number;
	health: number;
	max_health: number;
	tier: number;
	tribe: string;
	keywords: string[];
	divine_shield: boolean;
	golden: boolean;
}

export interface SelfSnapshot {
	player_id: string;
	name: string;
	health: number;
	armor: number;
	tavern_tier: number;
	upgrade_cost: number;
	locked: boolean;
	board: MinionSnapshot[];
	hand: MinionSnapshot[];
	shop: (MinionSnapshot | null)[];
	gold: number;
	max_gold: number;
	frozen: boolean;
	hero: HeroSnapshot | null;
	hero_power_uses_left: number;  // 1 = available, 0 = spent
}

export interface OpponentSnapshot {
	player_id: string;
	name: string;
	health: number;
	armor: number;
	tavern_tier: number;
	locked: boolean;
	board: MinionSnapshot[];
	hero: HeroSnapshot | null;
	is_bot: boolean;
}

export interface LeaderboardEntry {
	player_id: string;
	name: string;
	health: number;
	armor: number;
	is_bot: boolean;
	last_combat_board: MinionSnapshot[];
}

export type Phase = "buy" | "combat" | "game_over";

export type CombatEvent =
	| {
			type: "attack";
			attacker_id: string;
			attacker_name: string;
			attacker_attack: number;
			defender_id: string;
			defender_name: string;
			defender_attack: number;
	  }
	| {
			type: "damage_dealt";
			attacker_id: string;
			attacker_remaining_hp: number;
			attacker_divine_shield: boolean;
			damage_to_attacker: number;
			defender_id: string;
			defender_remaining_hp: number;
			defender_divine_shield: boolean;
			damage_to_defender: number;
	  }
	| {
			type: "damage";
			target_id: string;
			target_name: string;
			amount: number;
			remaining_health: number;
			remaining_divine_shield: boolean;
	  }
	| {
			type: "death";
			minion_id: string;
			minion_name: string;
			player_idx: number;
	  }
	| {
			type: "reborn_trigger";
			minion_id: string;
			minion_name: string;
			player_idx: number;
			position: number;
			minion: MinionSnapshot;
	  }
	| {
			type: "cleave_splash";
			attacker_id: string;
			attacker_name: string;
			target_id: string;
			target_name: string;
			amount: number;
			remaining_health: number;
			remaining_divine_shield: boolean;
	  }
	| {
			type: "buff";
			target_id: string;
			target_name: string;
			attack: number;
			health: number;
	  }
	| {
			type: "summon";
			card_id: string;
			minion: MinionSnapshot;
			side: number;
			to_enemy: boolean;
	  }
	| {
			type: "keyword_added";
			target_id: string;
			keyword: string;
	  };

export interface CombatMeta {
	players: [string, string];
	initial_a: MinionSnapshot[];
	initial_b: MinionSnapshot[];
}

export interface CombatResultMsg {
	type: "combat_result";
	round: number;
	winner_player: string | null;
	damage: number;
	health: Record<string, number>;
}

export type Intent =
	| { type: "login"; name: string }
	| { type: "reconnect"; player_id: string }
	| { type: "queue" }
	| { type: "hero_pick"; index: number }
	| { type: "use_hero_power" }
	| { type: "use_hero_power"; target_zone: "shop" | "hand"; target_index: number }
	| { type: "buy"; shop_index: number }
	| { type: "play"; hand_index: number }
	| { type: "sell"; board_index: number }
	| { type: "reorder"; from_index: number; to_index: number }
	| { type: "freeze" }
	| { type: "refresh" }
	| { type: "upgrade" }
	| { type: "lock" }
	| { type: "discover_pick"; index: number }
	| { type: "concede" };
