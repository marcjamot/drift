import type { CombatEvent, CombatMeta, CombatResultMsg, Intent, OpponentSnapshot, Phase, SelfSnapshot } from "./types.js";

export const gs = $state({
	screen: "login" as "login" | "queued" | "game" | "game_over",

	playerId: null as string | null,
	playerName: null as string | null,
	matchId: null as string | null,
	opponentName: null as string | null,

	round: 0,
	phase: null as Phase | null,
	buySecondsLeft: null as number | null,
	self: null as SelfSnapshot | null,
	opponent: null as OpponentSnapshot | null,
	combatLog: [] as CombatEvent[],
	combatMeta: null as CombatMeta | null,
	combatResult: null as CombatResultMsg | null,
	error: null as string | null,
	gameOverWinner: null as string | null,
	connected: false,
	discoverOptions: null as import("./types.js").MinionSnapshot[] | null,
});

let _frozenRound = -1;
let _frozenOpponent: OpponentSnapshot | null = null;

let ws: WebSocket | null = null;
let buyTimerHandle: number | null = null;

export function connect(url = "ws://localhost:8765") {
	if (ws) return;
	ws = new WebSocket(url);

	ws.onopen = () => {
		gs.connected = true;
		gs.error = null;
		const stored = localStorage.getItem("drift_player_id");
		if (stored) send({ type: "reconnect", player_id: stored });
	};

	ws.onclose = () => {
		gs.connected = false;
		ws = null;
		setTimeout(() => connect(url), 2000);
	};

	ws.onerror = () => {
		gs.error = "Connection error";
	};

	ws.onmessage = (ev) => {
		try {
			handle(JSON.parse(ev.data));
		} catch {
			// ignore malformed
		}
	};
}

export function send(intent: Intent) {
	if (ws?.readyState === WebSocket.OPEN) {
		ws.send(JSON.stringify(intent));
	}
}

function stopBuyTimer() {
	if (buyTimerHandle !== null) {
		clearInterval(buyTimerHandle);
		buyTimerHandle = null;
	}
}

function startBuyTimer() {
	stopBuyTimer();
	if (gs.buySecondsLeft === null) return;
	buyTimerHandle = window.setInterval(() => {
		if (gs.phase !== "buy" || gs.buySecondsLeft === null) {
			stopBuyTimer();
			return;
		}
		gs.buySecondsLeft = Math.max(0, gs.buySecondsLeft - 1);
	}, 1000);
}

function handle(msg: Record<string, unknown>) {
	switch (msg.type as string) {
		case "welcome":
			gs.playerId = msg.player_id as string;
			gs.playerName = msg.name as string;
			localStorage.setItem("drift_player_id", gs.playerId);
			return;

		case "reconnected":
			gs.playerId = msg.player_id as string;
			gs.screen = "game";
			return;

		case "queued":
			gs.screen = "queued";
			return;

		case "match_start":
			gs.matchId = msg.match_id as string;
			gs.opponentName = msg.opponent as string;
			gs.screen = "game";
			gs.buySecondsLeft = null;
			gs.combatLog = [];
			gs.combatMeta = null;
			gs.combatResult = null;
			_frozenRound = -1;
			_frozenOpponent = null;
			return;

		case "state": {
			const round = msg.round as number;
			const phase = msg.phase as Phase;
			gs.round = round;
			gs.phase = phase;
			gs.screen = phase === "game_over" ? "game_over" : "game";
			gs.gameOverWinner = phase === "game_over" ? ((msg.winner as string | null) ?? null) : null;
			gs.buySecondsLeft = phase === "buy" ? (msg.buy_seconds_left as number | null) : null;
			gs.self = msg.self as SelfSnapshot;

			if (phase === "buy") {
				startBuyTimer();
				if (round !== _frozenRound) {
					_frozenRound = round;
					_frozenOpponent = msg.opponent as OpponentSnapshot;
				}
				gs.opponent = _frozenOpponent;
			} else {
				stopBuyTimer();
				gs.opponent = msg.opponent as OpponentSnapshot;
			}
			return;
		}

		case "combat_start":
			gs.phase = "combat";
			gs.buySecondsLeft = null;
			stopBuyTimer();
			gs.combatLog = [];
			gs.combatMeta = null;
			gs.combatResult = null;
			return;

		case "combat_log":
			gs.combatMeta = {
				players: msg.players as [string, string],
				initial_a: msg.initial_a as import("./types.js").MinionSnapshot[],
				initial_b: msg.initial_b as import("./types.js").MinionSnapshot[],
			};
			gs.combatLog = msg.events as CombatEvent[];
			return;

		case "combat_result":
			gs.combatResult = msg as unknown as CombatResultMsg;
			return;

		case "game_over":
			gs.gameOverWinner = msg.winner as string;
			gs.screen = "game_over";
			gs.buySecondsLeft = null;
			stopBuyTimer();
			return;

		case "error":
			if (msg.message === "unknown player_id") {
				localStorage.removeItem("drift_player_id");
				gs.playerId = null;
				return;
			}
			gs.error = msg.message as string;
			setTimeout(() => (gs.error = null), 4000);
			return;

		case "discover":
			gs.discoverOptions = msg.options as import("./types.js").MinionSnapshot[];
			return;

		case "action_result":
			if ((msg.action as string) === "discover_pick" && !msg.error) {
				gs.discoverOptions = null;
			}
			if (msg.error) {
				gs.error = msg.error as string;
				setTimeout(() => (gs.error = null), 3000);
			}
			return;
	}
}
