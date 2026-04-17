import { handleMessage } from "./handler.js";
import type { Intent } from "./types.js";
import { ui } from "./ui.svelte.js";

export const connection = $state({
	connected: false,
	playerId: null as string | null,
	playerName: null as string | null,
	matchId: null as string | null,
});

let ws: WebSocket | null = null;
let reconnect = true;

export function connect(url = "ws://localhost:8765") {
	if (ws) return;
	reconnect = true;
	ws = new WebSocket(url);

	ws.onopen = () => {
		connection.connected = true;
		ui.error = null;
		const stored = localStorage.getItem("drift_player_id");
		if (stored) send({ type: "reconnect", player_id: stored });
	};

	ws.onclose = () => {
		connection.connected = false;
		ws = null;
		if (reconnect) setTimeout(() => connect(url), 2000);
	};

	ws.onerror = () => {
		ui.error = "Connection error";
	};

	ws.onmessage = (ev) => {
		try {
			handleMessage(JSON.parse(ev.data));
		} catch {
		}
	};
}

export function send(intent: Intent) {
	if (ws?.readyState === WebSocket.OPEN) {
		ws.send(JSON.stringify(intent));
	}
}

export function disconnect() {
	reconnect = false;
	connection.connected = false;
	ws?.close();
	ws = null;
}
