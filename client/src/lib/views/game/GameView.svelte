<script lang="ts">
	import { gs, send } from "$lib/game/store.svelte.js";
	import ShopView from "./shop/ShopView.svelte";
	import CombatView from "./combat/CombatView.svelte";

	let concedeArmed = $state(false);
	let concedeTimer = 0;
	let healthFlash = $state(false);
	let prevHealth = -1;

	$effect(() => {
		if (!gs.self) return;
		const h = gs.self.health;
		if (prevHealth !== -1 && h < prevHealth) {
			healthFlash = true;
			setTimeout(() => (healthFlash = false), 900);
		}
		prevHealth = h;
	});

	// Show combat while phase is combat OR while combatMeta exists (animation in progress / holding result).
	// CombatView clears combatMeta when it's fully done, which drops this back to false.
	const showCombat = $derived(gs.phase === "combat" || gs.combatMeta !== null);

	function lock() {
		send({ type: "lock" });
	}

	function concede() {
		if (!concedeArmed) {
			concedeArmed = true;
			clearTimeout(concedeTimer);
			concedeTimer = setTimeout(() => (concedeArmed = false), 3000) as unknown as number;
		} else {
			clearTimeout(concedeTimer);
			concedeArmed = false;
			send({ type: "concede" });
		}
	}
</script>

{#if gs.self && gs.opponent}
	<div class="game-shell" class:combat-mode={gs.phase === "combat"} class:buy-mode={gs.phase === "buy"}>
		<header class="topbar">
			<div class="identity">
				<div class="nameplate">{gs.self.name}</div>
				<div class="round-chip">Round {gs.round}</div>
				<div class="health-chip" class:low={gs.self.health <= 15}>♥ {gs.self.health}</div>
				<div class="health-chip enemy" class:low={gs.opponent.health <= 15}>
					{gs.opponent.name} · ♥ {gs.opponent.health}
				</div>
			</div>

			{#if !showCombat && gs.phase === "buy"}
				<div class="controls">
					<span class="turn-timer" class:urgent={(gs.buySecondsLeft ?? 99) <= 5}>
						{gs.buySecondsLeft ?? 0}s
					</span>
					<button class="btn concede" onclick={concede}>
						{concedeArmed ? "Confirm?" : "Concede"}
					</button>
					<button class="btn end-turn" onclick={lock} disabled={gs.self.locked}>
						{gs.self.locked ? "✓ Waiting…" : "End Turn"}
					</button>
				</div>
			{:else}
				<div class="combat-status">
					<span class="phase-chip">Combat</span>
				</div>
			{/if}
		</header>

		{#if !showCombat && gs.phase === "buy"}
			<ShopView {healthFlash} />
		{:else}
			<CombatView {healthFlash} />
		{/if}
	</div>
{/if}

<style>
	.game-shell {
		display: flex;
		flex-direction: column;
		height: 100vh;
		padding: 18px;
		gap: 18px;
		overflow: hidden;
	}
	.game-shell.combat-mode {
		background: radial-gradient(circle at center, #2b2320 0%, transparent 32%),
			linear-gradient(180deg, #140f0d 0%, #090b0f 100%);
	}

	.topbar {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 16px;
		padding: 14px 18px;
		border-radius: 22px;
		background: rgba(12, 15, 19, 0.78);
		border: 1px solid #2f3944;
		backdrop-filter: blur(10px);
	}
	.identity,
	.controls,
	.combat-status {
		display: flex;
		align-items: center;
		gap: 10px;
		flex-wrap: wrap;
	}

	.nameplate,
	.round-chip,
	.health-chip,
	.phase-chip {
		padding: 6px 12px;
		border-radius: 999px;
		border: 1px solid #37424d;
		background: #171c22;
	}
	.nameplate {
		font-size: 18px;
		font-weight: 700;
		color: #fff4df;
	}
	.health-chip.low {
		color: #ffb0b0;
		border-color: #8a4545;
	}
	.health-chip.enemy {
		color: #d9ccbb;
	}

	.turn-timer {
		min-width: 58px;
		text-align: center;
		padding: 8px 12px;
		border-radius: 999px;
		border: 1px solid #6a7d92;
		background: #1d2833;
		color: #e8f0fa;
		font-size: 13px;
		font-weight: 700;
	}
	.turn-timer.urgent {
		border-color: #c77474;
		background: #3a1e1e;
		color: #ffd6d6;
	}

	.btn {
		font-family: inherit;
		font-size: 13px;
		padding: 8px 14px;
		border-radius: 999px;
		border: 1px solid #4b5563;
		background: #1b2128;
		color: #f0e7d7;
		cursor: pointer;
		transition:
			background 0.15s,
			border-color 0.15s,
			color 0.15s,
			transform 0.15s;
		white-space: nowrap;
	}
	.btn:hover:not(:disabled) {
		background: #232b35;
		border-color: #8f7a57;
		transform: translateY(-1px);
	}
	.btn:disabled {
		opacity: 0.4;
		cursor: default;
	}
	.btn.end-turn {
		background: #26462f;
		border-color: #5f9d69;
		color: #e0ffdd;
		min-width: 140px;
	}
	.btn.concede {
		background: transparent;
		border-color: transparent;
		color: #b58f8f;
	}

	@media (max-width: 900px) {
		.game-shell {
			padding: 12px;
			gap: 12px;
		}
		.topbar {
			padding: 12px;
		}
	}
</style>
