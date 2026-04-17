import type { LeaderboardEntry, OpponentSnapshot, Phase, SelfSnapshot } from "./types.js";

export const match = $state({
	round: 0,
	phase: null as Phase | null,
	buySecondsLeft: null as number | null,
	self: null as SelfSnapshot | null,
	opponent: null as OpponentSnapshot | null,
	leaderboard: [] as LeaderboardEntry[],
});
