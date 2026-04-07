export interface MinionSnapshot {
	instance_id: string;
	card_id: string;
	name: string;
	description: string;
	attack: number;
	health: number;
	max_health: number;
	tier: number;
	keywords: string[];
	divine_shield: boolean;
	golden: boolean;
}

export interface SelfSnapshot {
	player_id: string;
	name: string;
	health: number;
	tavern_tier: number;
	upgrade_cost: number;
	locked: boolean;
	board: MinionSnapshot[];
	hand: MinionSnapshot[];
	shop: (MinionSnapshot | null)[];
	gold: number;
	max_gold: number;
	frozen: boolean;
}

export interface OpponentSnapshot {
	player_id: string;
	name: string;
	health: number;
	tavern_tier: number;
	locked: boolean;
	board: MinionSnapshot[];
}

export type Phase = "buy" | "combat" | "game_over";

export interface CombatEvent {
	type: string;
	[key: string]: unknown;
}

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
	| { type: "buy"; shop_index: number }
	| { type: "play"; hand_index: number }
	| { type: "sell"; board_index: number }
	| { type: "reorder"; from_index: number; to_index: number }
	| { type: "freeze" }
	| { type: "refresh" }
	| { type: "upgrade" }
	| { type: "lock" }
	| { type: "concede" };
