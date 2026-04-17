import type { HeroSnapshot, MinionSnapshot } from "./types.js";

export type Screen = "login" | "queued" | "hero_select" | "game" | "game_over";

export const ui = $state({
	screen: "login" as Screen,
	error: null as string | null,
	discoverOptions: null as MinionSnapshot[] | null,
	heroOptions: null as HeroSnapshot[] | null,
	queuedCount: 0,
	totalSlots: 8,
	queueSecondsLeft: null as number | null,
	canSkipQueueWait: false,
	gameOverWinner: null as string | null,
	gameOverPlacement: null as number | null,
	gameOverMmrDelta: null as number | null,
});
