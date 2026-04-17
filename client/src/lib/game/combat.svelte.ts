import type { CombatEvent, CombatMeta, CombatResultMsg } from "./types.js";

export const combat = $state({
	combatLog: [] as CombatEvent[],
	combatMeta: null as CombatMeta | null,
	combatResult: null as CombatResultMsg | null,
});
