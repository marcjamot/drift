import { combat } from "./combat.svelte.js";
import { connection } from "./connection.svelte.js";
import { match } from "./match.svelte.js";
import type { CombatEvent, CombatResultMsg, HeroSnapshot, LeaderboardEntry, MinionSnapshot, OpponentSnapshot, Phase, QueuedMsg, SelfSnapshot } from "./types.js";
import { ui } from "./ui.svelte.js";

let frozenRound = -1;
let frozenOpponent: OpponentSnapshot | null = null;
let buyTimerHandle: number | null = null;
let queueTimerHandle: number | null = null;

function stopBuyTimer() {
	if (buyTimerHandle !== null) {
		clearInterval(buyTimerHandle);
		buyTimerHandle = null;
	}
}

function startBuyTimer() {
	stopBuyTimer();
	if (match.buySecondsLeft === null) return;
	buyTimerHandle = window.setInterval(() => {
		if (match.phase !== "buy" || match.buySecondsLeft === null) {
			stopBuyTimer();
			return;
		}
		match.buySecondsLeft = Math.max(0, match.buySecondsLeft - 1);
	}, 1000);
}

function stopQueueTimer() {
	if (queueTimerHandle !== null) {
		clearInterval(queueTimerHandle);
		queueTimerHandle = null;
	}
}

function startQueueTimer() {
	stopQueueTimer();
	if (ui.queueSecondsLeft === null) return;
	queueTimerHandle = window.setInterval(() => {
		if (ui.screen !== "queued" || ui.queueSecondsLeft === null) {
			stopQueueTimer();
			return;
		}
		ui.queueSecondsLeft = Math.max(0, ui.queueSecondsLeft - 1);
	}, 1000);
}

function showError(message: string, ms: number) {
	ui.error = message;
	setTimeout(() => (ui.error = null), ms);
}

function resetCombat() {
	combat.combatLog = [];
	combat.combatMeta = null;
	combat.combatResult = null;
}

function resetMatchStart() {
	stopQueueTimer();
	ui.heroOptions = null;
	ui.queuedCount = 0;
	ui.totalSlots = 8;
	ui.queueSecondsLeft = null;
	ui.canSkipQueueWait = false;
	ui.gameOverWinner = null;
	ui.gameOverPlacement = null;
	ui.gameOverMmrDelta = null;
	match.buySecondsLeft = null;
	match.leaderboard = [];
	resetCombat();
	frozenRound = -1;
	frozenOpponent = null;
}

export function handleMessage(msg: Record<string, unknown>) {
	switch (msg.type as string) {
		case "welcome":
			connection.playerId = msg.player_id as string;
			connection.playerName = msg.name as string;
			localStorage.setItem("drift_player_id", connection.playerId);
			return;
		case "reconnected":
			connection.playerId = msg.player_id as string;
			stopQueueTimer();
			ui.screen = "game";
			return;
		case "queued": {
			const queued = msg as unknown as QueuedMsg;
			ui.queuedCount = queued.queued_count;
			ui.totalSlots = queued.total_slots;
			ui.queueSecondsLeft = queued.seconds_left;
			ui.canSkipQueueWait = queued.can_skip_wait;
			ui.screen = "queued";
			startQueueTimer();
			return;
		}
		case "hero_options":
			stopQueueTimer();
			ui.heroOptions = msg.options as HeroSnapshot[];
			ui.screen = "hero_select";
			return;
		case "match_start":
			connection.matchId = msg.match_id as string;
			ui.screen = "game";
			resetMatchStart();
			return;
		case "state": {
			const round = msg.round as number;
			const phase = msg.phase as Phase;
			match.round = round;
			match.phase = phase;
			ui.screen = phase === "game_over" ? "game_over" : "game";
			match.buySecondsLeft = phase === "buy" ? (msg.buy_seconds_left as number | null) : null;
			match.self = msg.self as SelfSnapshot;
			match.leaderboard = (msg.leaderboard as LeaderboardEntry[]) ?? [];

			if (phase === "buy") {
				startBuyTimer();
				if (round !== frozenRound) {
					frozenRound = round;
					frozenOpponent = (msg.opponent as OpponentSnapshot) ?? null;
				}
				match.opponent = frozenOpponent;
			} else {
				stopBuyTimer();
				match.opponent = (msg.opponent as OpponentSnapshot) ?? null;
			}
			return;
		}
		case "combat_start":
			match.phase = "combat";
			match.buySecondsLeft = null;
			stopBuyTimer();
			resetCombat();
			return;
		case "combat_log": {
			const pre_health: Record<string, number> = {};
			const pre_armor: Record<string, number> = {};
			if (match.self) {
				pre_health[match.self.player_id] = match.self.health;
				pre_armor[match.self.player_id] = match.self.armor;
			}
			if (match.opponent) {
				pre_health[match.opponent.player_id] = match.opponent.health;
				pre_armor[match.opponent.player_id] = match.opponent.armor;
			}
			combat.combatMeta = {
				players: msg.players as [string, string],
				is_ghost: (msg.is_ghost as boolean) ?? false,
				initial_a: msg.initial_a as MinionSnapshot[],
				initial_b: msg.initial_b as MinionSnapshot[],
				pre_health,
				pre_armor,
			};
			combat.combatLog = msg.events as CombatEvent[];
			return;
		}
		case "combat_result":
			combat.combatResult = msg as unknown as CombatResultMsg;
			return;
		case "game_over":
			ui.gameOverWinner = (msg.winner as string | null) ?? null;
			ui.gameOverPlacement = (msg.placement as number | null) ?? null;
			ui.gameOverMmrDelta = (msg.mmr_delta as number | null) ?? null;
			ui.screen = "game_over";
			match.buySecondsLeft = null;
			stopBuyTimer();
			return;
		case "error":
			if (msg.message === "unknown player_id") {
				localStorage.removeItem("drift_player_id");
				connection.playerId = null;
				return;
			}
			showError(msg.message as string, 4000);
			return;
		case "discover_options":
			ui.discoverOptions = msg.options as MinionSnapshot[];
			return;
		case "action_result":
			if ((msg.action as string) === "discover_pick" && !msg.error) {
				ui.discoverOptions = null;
			}
			if (msg.error) {
				showError(msg.error as string, 3000);
			}
			return;
	}
}
