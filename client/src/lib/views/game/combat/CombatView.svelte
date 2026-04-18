<script lang="ts">
	import { untrack } from "svelte";
	import { combat } from "$lib/game/combat.svelte.js";
	import { connection } from "$lib/game/connection.svelte.js";
	import { match } from "$lib/game/match.svelte.js";
	import type { CombatEvent, MinionSnapshot } from "$lib/game/types.js";
	import EnemyInfo from "./EnemyInfo.svelte";
	import EnemyBoard from "./EnemyBoard.svelte";
	import PlayerBoard from "./PlayerBoard.svelte";
	import PlayerInfo from "./PlayerInfo.svelte";

	interface Props {
		healthFlash: boolean;
	}
	let { healthFlash }: Props = $props();

	const COMBAT_RESULT_HOLD_MS = 1400;

	type AnimPhase = "idle" | "animating" | "done";
	let animPhase = $state<AnimPhase>("idle");
	let animSelfBoard = $state<MinionSnapshot[]>([]);
	let animOppBoard = $state<MinionSnapshot[]>([]);
	let animStricken = $state(new Set<string>());
	let animImpact = $state(new Set<string>());
	let animDying = $state(new Set<string>());
	let animNewIds = $state(new Set<string>());
	let animBadges = $state(new Map<string, string>());
	let animCleaveSplash = $state(new Set<string>());
	let animCardStyles = $state(new Map<string, string>());
	let animText = $state("");
	let animStarted = false;
	let animShake = $state(false);

	type DmgNumber = { id: number; cardId: string; value: number; x: number; y: number; enemy: boolean };
	let dmgNumbers = $state<DmgNumber[]>([]);
	let dmgSeq = 0;
	let arenaEl = $state<HTMLElement | null>(null);
	const dmgTimeouts: Record<string, number> = {};

	$effect(() => {
		const log = combat.combatLog;
		const meta = combat.combatMeta;
		if (!meta || !connection.playerId) return;
		if (animStarted) return;
		animStarted = true;
		const isSelfA = meta.players[0] === connection.playerId;
		untrack(() => {
			animSelfBoard = isSelfA ? [...meta.initial_a] : [...meta.initial_b];
			animOppBoard = isSelfA ? [...meta.initial_b] : [...meta.initial_a];
			animPhase = "animating";
		});
		runCombatAnim(log, isSelfA);
	});

	// After animation finishes and we're back in buy phase, hold the result
	// briefly then clear combat data so GameView unmounts this view.
	$effect(() => {
		if (match.phase !== "buy") return;
		if (animPhase === "idle") return;
		if (animPhase === "animating") return;
		if (!combat.combatResult) return;
		const resetTimer = setTimeout(() => {
			animStarted = false;
			animPhase = "idle";
			animText = "";
			animStricken = new Set();
			animImpact = new Set();
			animDying = new Set();
			animNewIds = new Set();
			animBadges = new Map();
			animCleaveSplash = new Set();
			animCardStyles = new Map();
			clearDamageNumbers();
			combat.combatLog = [];
			combat.combatMeta = null;
			combat.combatResult = null;
		}, COMBAT_RESULT_HOLD_MS);
		return () => clearTimeout(resetTimer);
	});

	function sleep(ms: number) {
		return new Promise<void>((r) => setTimeout(r, ms));
	}

	function clearDamageNumbers() {
		for (const timeout of Object.values(dmgTimeouts)) clearTimeout(timeout);
		for (const cardId of Object.keys(dmgTimeouts)) delete dmgTimeouts[cardId];
		dmgNumbers = [];
	}

	function updateMinionState(id: string, hp: number, divineShield?: boolean) {
		animSelfBoard = animSelfBoard.map((m) =>
			m.instance_id === id ? { ...m, health: hp, divine_shield: divineShield ?? m.divine_shield } : m
		);
		animOppBoard = animOppBoard.map((m) =>
			m.instance_id === id ? { ...m, health: hp, divine_shield: divineShield ?? m.divine_shield } : m
		);
	}

	function updateMinionBuff(id: string, atk: number, hp: number) {
		animSelfBoard = animSelfBoard.map((m) =>
			m.instance_id === id ? { ...m, attack: m.attack + atk, health: m.health + hp } : m
		);
		animOppBoard = animOppBoard.map((m) =>
			m.instance_id === id ? { ...m, attack: m.attack + atk, health: m.health + hp } : m
		);
	}

	function insertMinion(board: MinionSnapshot[], minion: MinionSnapshot, position: number) {
		const withoutExisting = board.filter((m) => m.instance_id !== minion.instance_id);
		const idx = Math.max(0, Math.min(position, withoutExisting.length));
		return [...withoutExisting.slice(0, idx), minion, ...withoutExisting.slice(idx)];
	}

	function applyLunge(attackerId: string, defenderId: string) {
		const aEl = document.getElementById("card-" + attackerId);
		const dEl = document.getElementById("card-" + defenderId);
		if (!aEl || !dEl) return;
		const aR = aEl.getBoundingClientRect();
		const dR = dEl.getBoundingClientRect();
		const dx = dR.left + dR.width / 2 - (aR.left + aR.width / 2);
		const dy = dR.top + dR.height / 2 - (aR.top + aR.height / 2);
		animCardStyles = new Map([[attackerId, `transform: translate(${dx}px, ${dy}px) scale(0.93);`]]);
	}

	function spawnDmgNumber(cardId: string, value: number, isEnemyCard: boolean) {
		if (value <= 0 || !arenaEl) return;
		const cardEl = document.getElementById("card-" + cardId);
		if (!cardEl) return;
		const cR = cardEl.getBoundingClientRect();
		const aR = arenaEl.getBoundingClientRect();
		const x = cR.left + cR.width / 2 - aR.left;
		const y = cR.top - aR.top + 10;
		const existing = dmgNumbers.find((n) => n.cardId === cardId);
		if (existing) {
			dmgNumbers = dmgNumbers.map((n) =>
				n.cardId === cardId ? { ...n, value: n.value + value, x, y, enemy: isEnemyCard } : n
			);
		} else {
			const id = ++dmgSeq;
			dmgNumbers = [...dmgNumbers, { id, cardId, value, x, y, enemy: isEnemyCard }];
		}
		const prevTimeout = dmgTimeouts[cardId];
		if (prevTimeout !== undefined) clearTimeout(prevTimeout);
		const timeout = window.setTimeout(() => {
			dmgNumbers = dmgNumbers.filter((n) => n.cardId !== cardId);
			delete dmgTimeouts[cardId];
		}, 950);
		dmgTimeouts[cardId] = timeout;
	}

	async function runCombatAnim(events: CombatEvent[], isSelfA: boolean) {
		for (const e of events) {
			if (e.type === "attack") {
				const aid = e.attacker_id as string;
				const did = e.defender_id as string;
				animStricken = new Set();
				animImpact = new Set();
				animCardStyles = new Map();
				await sleep(120);
				animText = `${e.attacker_name} attacks ${e.defender_name}`;
				await sleep(900);
				await sleep(16);
				applyLunge(aid, did);
				await sleep(300);
			} else if (e.type === "damage_dealt") {
				const aid = e.attacker_id as string;
				const did = e.defender_id as string;
				const defDmg = e.damage_to_defender as number;
				const attackerIsOpp = animOppBoard.some((m) => m.instance_id === aid);
				if (defDmg > 0) spawnDmgNumber(did, defDmg, !attackerIsOpp);
				if (defDmg >= 4) { animShake = true; setTimeout(() => (animShake = false), 380); }
				const atkDmg = e.damage_to_attacker as number;
				animStricken = new Set([...(atkDmg > 0 ? [aid] : []), ...(defDmg > 0 ? [did] : [])]);
				animImpact = new Set([did]);
				animCardStyles = new Map();
				animText = "✦ Impact";
				updateMinionState(aid, e.attacker_remaining_hp as number, e.attacker_divine_shield as boolean | undefined);
				updateMinionState(did, e.defender_remaining_hp as number, e.defender_divine_shield as boolean | undefined);
				await sleep(180);
				animImpact = new Set();
				await sleep(500);
				animStricken = new Set();
			} else if (e.type === "death") {
				const mid = e.minion_id as string;
				animDying = new Set([...animDying, mid]);
				animText = `${e.minion_name} falls`;
				await sleep(550);
				animSelfBoard = animSelfBoard.filter((m) => m.instance_id !== mid);
				animOppBoard = animOppBoard.filter((m) => m.instance_id !== mid);
				animDying = new Set([...animDying].filter((id) => id !== mid));
			} else if (e.type === "buff") {
				animText = `${e.target_name} grows stronger`;
				updateMinionBuff(e.target_id as string, e.attack as number, e.health as number);
				await sleep(600);
			} else if (e.type === "summon") {
				const m = e.minion as MinionSnapshot;
				if (m) {
					const side = e.side as number;
					const isOppSide = isSelfA ? side === 1 : side === 0;
					animNewIds = new Set([m.instance_id]);
					if (isOppSide) animOppBoard = insertMinion(animOppBoard, m, e.position);
					else animSelfBoard = insertMinion(animSelfBoard, m, e.position);
					animText = `${m.name} summoned`;
					await sleep(600);
					setTimeout(() => (animNewIds = new Set()), 500);
				}
			} else if (e.type === "reborn_trigger") {
				const m = e.minion;
				const isOppSide = isSelfA ? e.player_idx === 1 : e.player_idx === 0;
				if (isOppSide) animOppBoard = insertMinion(animOppBoard, m, e.position);
				else animSelfBoard = insertMinion(animSelfBoard, m, e.position);
				animNewIds = new Set([m.instance_id]);
				animBadges = new Map([[m.instance_id, "Reborn!"]]);
				animText = `${m.name} returns`;
				await sleep(700);
				animBadges = new Map();
				animNewIds = new Set();
			} else if (e.type === "cleave_splash") {
				const targetIsOpp = animOppBoard.some((m) => m.instance_id === e.target_id);
				if (e.amount > 0) spawnDmgNumber(e.target_id, e.amount, targetIsOpp);
				animStricken = new Set([...animStricken, e.target_id]);
				animImpact = new Set([...animImpact, e.target_id]);
				animCleaveSplash = new Set([...animCleaveSplash, e.target_id]);
				animText = "Cleave";
				updateMinionState(e.target_id, e.remaining_health, e.remaining_divine_shield);
				await sleep(260);
				animImpact = new Set([...animImpact].filter((id) => id !== e.target_id));
				animCleaveSplash = new Set([...animCleaveSplash].filter((id) => id !== e.target_id));
				await sleep(120);
				animStricken = new Set([...animStricken].filter((id) => id !== e.target_id));
			} else if (e.type === "damage") {
				const targetId = e.target_id as string;
				const amount = e.amount as number;
				const targetIsOpp = animOppBoard.some((m) => m.instance_id === targetId);
				if (amount > 0) spawnDmgNumber(targetId, amount, targetIsOpp);
				updateMinionState(targetId, e.remaining_health as number, e.remaining_divine_shield as boolean | undefined);
				await sleep(120);
			}
		}

		animStricken = new Set();
		animImpact = new Set();
		animCleaveSplash = new Set();
		animCardStyles = new Map();
		animDying = new Set();
		animBadges = new Map();
		clearDamageNumbers();

		const result = combat.combatResult;
		if (result) {
			if (result.winner_player === null) animText = "Tie — no damage dealt";
			else if (result.winner_player === connection.playerId) animText = "You won this round";
			else animText = "You lost this round";
		} else {
			animText = "";
		}
		animPhase = "done";
		await sleep(events.length > 0 ? 900 : 1400);
	}
</script>

<div class="battle-arena" class:shaking={animShake} bind:this={arenaEl}>
	{#if match.opponent && combat.combatMeta}
		{@const pid = match.opponent.player_id}
		{@const health = animPhase === "done" && combat.combatResult
			? (combat.combatResult.health[pid] ?? match.opponent.health)
			: (combat.combatMeta.pre_health[pid] ?? match.opponent.health)}
		{@const armor = animPhase === "done" && combat.combatResult
			? match.opponent.armor
			: (combat.combatMeta.pre_armor[pid] ?? match.opponent.armor)}
		<EnemyInfo
			name={match.opponent.name}
			{health}
			{armor}
			hero={match.opponent.hero ?? null}
			isGhost={match.opponent.is_ghost}
		/>
	{:else if match.opponent}
		<EnemyInfo
			name={match.opponent.name}
			health={match.opponent.health}
			armor={match.opponent.armor}
			hero={match.opponent.hero ?? null}
			isGhost={match.opponent.is_ghost}
		/>
	{/if}

	<EnemyBoard
		minions={animOppBoard}
		strickenIds={animStricken}
		impactIds={animImpact}
		dyingIds={animDying}
		newIds={animPhase !== "idle" ? animNewIds : new Set()}
		badgeTextById={animBadges}
		cleaveSplashIds={animCleaveSplash}
		cardStyles={animCardStyles}
	/>

	<div class="arena-divider">
		{#if animPhase === "done" && combat.combatResult && match.self}
			<div
				class="result-pill"
				class:win={combat.combatResult.winner_player === match.self.player_id}
				class:loss={combat.combatResult.winner_player !== null && combat.combatResult.winner_player !== match.self.player_id}
			>
				{#if combat.combatResult.winner_player === null}
					Tie — no damage
				{:else if combat.combatResult.winner_player === match.self.player_id}
					You win · opponent takes {combat.combatResult.damage}
				{:else}
					You lose · you take {combat.combatResult.damage}
				{/if}
			</div>
		{:else}
			<div class="combat-pill">{animText || "⚔ Combat"}</div>
		{/if}
	</div>

	<PlayerBoard
		minions={animSelfBoard}
		strickenIds={animStricken}
		impactIds={animImpact}
		dyingIds={animDying}
		newIds={animPhase !== "idle" ? animNewIds : new Set()}
		badgeTextById={animBadges}
		cleaveSplashIds={animCleaveSplash}
		cardStyles={animCardStyles}
		{healthFlash}
	/>

	{#if match.self && combat.combatMeta}
		{@const pid = match.self.player_id}
		{@const health = animPhase === "done" && combat.combatResult
			? (combat.combatResult.health[pid] ?? match.self.health)
			: (combat.combatMeta.pre_health[pid] ?? match.self.health)}
		{@const armor = animPhase === "done" && combat.combatResult
			? match.self.armor
			: (combat.combatMeta.pre_armor[pid] ?? match.self.armor)}
		<PlayerInfo name={match.self.name} {health} {armor} hero={match.self.hero ?? null} />
	{:else if match.self}
		<PlayerInfo name={match.self.name} health={match.self.health} armor={match.self.armor} hero={match.self.hero ?? null} />
	{/if}

	{#each dmgNumbers as n (n.id)}
		<div class="dmg-float" class:dmg-enemy={n.enemy} style="left:{n.x}px; top:{n.y}px;">-{n.value}</div>
	{/each}
</div>

<style>
	.battle-arena {
		position: relative;
		flex: 1;
		min-height: 0;
		display: flex;
		flex-direction: column;
		border-radius: 24px;
		background: rgba(10, 8, 6, 0.88);
		border: 1px solid #3a2e22;
		backdrop-filter: blur(8px);
		overflow: visible;
		animation: arena-in 0.52s cubic-bezier(0.22, 1, 0.36, 1) both, arena-border-in 0.9s ease-out both;
	}
	@keyframes arena-in {
		0% { opacity: 0; transform: scale(0.93) translateY(14px); }
		60% { opacity: 1; transform: scale(1.015) translateY(-2px); }
		100% { opacity: 1; transform: scale(1) translateY(0); }
	}
	@keyframes arena-border-in {
		0% { box-shadow: 0 0 0 0 #c87c3099; }
		35% { box-shadow: 0 0 40px 6px #c87c3055; }
		100% { box-shadow: none; }
	}
	.battle-arena.shaking {
		animation: arena-shake 0.34s ease-in-out;
	}
	@keyframes arena-shake {
		0%, 100% { transform: translateX(0); }
		18% { transform: translateX(-6px); }
		40% { transform: translateX(5px); }
		65% { transform: translateX(-3px); }
		82% { transform: translateX(2px); }
	}

	.arena-divider {
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 0 20px;
		height: 48px;
		border-top: 1px solid #241e16;
		border-bottom: 1px solid #241e16;
		flex-shrink: 0;
	}

	.combat-pill {
		padding: 7px 18px;
		border-radius: 999px;
		font-size: 14px;
		text-align: center;
		background: #1a1410;
		border: 1px solid #5a4833;
		color: #f4dfbb;
		animation: combat-entrance 0.4s cubic-bezier(0.34, 1.56, 0.64, 1) both;
	}
	.result-pill {
		padding: 7px 18px;
		border-radius: 999px;
		font-size: 14px;
		text-align: center;
		background: #1a1410;
		border: 1px solid #5a4833;
		color: #f4dfbb;
		animation: result-pop 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) both;
	}
	.result-pill.win {
		background: #0e1a10;
		border-color: #4b8052;
		color: #c8ffd0;
		box-shadow: 0 0 20px 2px #4b805233;
	}
	.result-pill.loss {
		background: #1e0f0f;
		border-color: #924c4c;
		color: #ffd0d0;
		box-shadow: 0 0 20px 2px #924c4c33;
	}
	@keyframes combat-entrance {
		from { opacity: 0; transform: scale(0.6); }
		to { opacity: 1; transform: scale(1); }
	}
	@keyframes result-pop {
		from { opacity: 0; transform: scale(0.5); }
		to { opacity: 1; transform: scale(1); }
	}

	.dmg-float {
		position: absolute;
		pointer-events: none;
		transform: translateX(-50%);
		font-size: 22px;
		font-weight: 800;
		color: #ff6b3d;
		text-shadow: 0 2px 8px #00000088;
		animation: dmg-rise 0.95s ease-out forwards;
		z-index: 30;
	}
	.dmg-float.dmg-enemy {
		color: #ff4444;
	}
	@keyframes dmg-rise {
		0% {
			opacity: 1;
			transform: translateX(-50%) translateY(0) scale(1.1);
		}
		20% {
			opacity: 1;
			transform: translateX(-50%) translateY(-8px) scale(1.3);
		}
		100% {
			opacity: 0;
			transform: translateX(-50%) translateY(-52px) scale(0.9);
		}
	}
</style>
