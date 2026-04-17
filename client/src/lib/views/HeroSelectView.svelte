<script lang="ts">
	import { gs, send } from "$lib/game/store.svelte.js";
	import type { HeroSnapshot } from "$lib/game/types.js";

	const TIMEOUT = 30;

	let picked = $state<number | null>(null);
	let secondsLeft = $state(TIMEOUT);
	let waiting = $state(false);

	$effect(() => {
		if (!gs.heroOptions) return;
		// Reset state whenever a new hero_options arrives
		picked = null;
		waiting = false;
		secondsLeft = TIMEOUT;

		const interval = setInterval(() => {
			secondsLeft = Math.max(0, secondsLeft - 1);
			if (secondsLeft === 0) {
				clearInterval(interval);
				if (picked === null) autopick();
			}
		}, 1000);

		return () => clearInterval(interval);
	});

	function pick(index: number) {
		if (waiting) return;
		picked = index;
		waiting = true;
		send({ type: "hero_pick", index });
	}

	function autopick() {
		if (picked === null) pick(0);
	}

	const urgentTimer = $derived(secondsLeft <= 10);
</script>

<div class="hero-select">
	<div class="header">
		<h2 class="title">Choose Your Hero</h2>
		<div class="timer" class:urgent={urgentTimer}>
			{secondsLeft}s
		</div>
	</div>

	{#if waiting}
		<p class="waiting-msg">Waiting for opponent…</p>
	{/if}

	<div class="cards">
		{#each (gs.heroOptions ?? []) as hero, i (hero.id)}
			<button
				class="hero-card"
				class:selected={picked === i}
				class:dimmed={picked !== null && picked !== i}
				disabled={waiting}
				onclick={() => pick(i)}
			>
				<div class="hero-name">{hero.name}</div>
				<div class="hero-divider"></div>
				<p class="hero-desc">{hero.description}</p>
				{#if picked === i}
					<div class="chosen-badge">Chosen</div>
				{/if}
			</button>
		{/each}
	</div>
</div>

<style>
	.hero-select {
		min-height: 100vh;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 40px;
		padding: 40px 24px;
		animation: fade-in 0.4s ease both;
	}
	@keyframes fade-in {
		from { opacity: 0; transform: translateY(16px); }
		to   { opacity: 1; transform: translateY(0); }
	}

	.header {
		display: flex;
		align-items: center;
		gap: 20px;
	}

	.title {
		font-size: 28px;
		font-weight: 700;
		color: #f2eadc;
		letter-spacing: 0.04em;
	}

	.timer {
		padding: 6px 14px;
		border-radius: 999px;
		border: 1px solid #6a7d92;
		background: #1d2833;
		color: #e8f0fa;
		font-size: 14px;
		font-weight: 700;
		min-width: 52px;
		text-align: center;
		transition: border-color 0.2s, background 0.2s, color 0.2s;
	}
	.timer.urgent {
		border-color: #c77474;
		background: #3a1e1e;
		color: #ffd6d6;
		animation: timer-pulse 0.75s ease-in-out infinite;
	}
	@keyframes timer-pulse {
		0%, 100% { box-shadow: none; }
		50% { box-shadow: 0 0 14px 3px #c7747455; }
	}

	.waiting-msg {
		color: #9aafb8;
		font-size: 14px;
		letter-spacing: 0.05em;
		animation: blink 1.6s ease-in-out infinite;
	}
	@keyframes blink {
		0%, 100% { opacity: 1; }
		50%       { opacity: 0.45; }
	}

	.cards {
		display: flex;
		gap: 24px;
		flex-wrap: wrap;
		justify-content: center;
	}

	.hero-card {
		position: relative;
		width: 220px;
		min-height: 280px;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 16px;
		padding: 28px 20px 24px;
		border-radius: 20px;
		border: 1px solid #2f3944;
		background: rgba(12, 15, 19, 0.85);
		cursor: pointer;
		font-family: inherit;
		color: #f2eadc;
		transition:
			transform 0.18s cubic-bezier(0.22, 1, 0.36, 1),
			border-color 0.18s,
			background 0.18s,
			box-shadow 0.18s,
			opacity 0.25s;
		backdrop-filter: blur(8px);
	}
	.hero-card:hover:not(:disabled):not(.selected) {
		transform: translateY(-6px) scale(1.02);
		border-color: #5a8abf;
		background: rgba(20, 30, 48, 0.9);
		box-shadow: 0 16px 40px #00000088, 0 0 0 1px #5a8abf44;
	}
	.hero-card:disabled {
		cursor: default;
	}
	.hero-card.selected {
		border-color: #71c186;
		background: rgba(14, 36, 20, 0.9);
		box-shadow: 0 0 0 2px #71c18666, 0 16px 40px #00000066;
		transform: translateY(-4px) scale(1.03);
	}
	.hero-card.dimmed {
		opacity: 0.35;
		transform: scale(0.97);
	}

	.hero-name {
		font-size: 18px;
		font-weight: 700;
		color: #e8d8c0;
		text-align: center;
		line-height: 1.3;
	}

	.hero-divider {
		width: 48px;
		height: 1px;
		background: linear-gradient(90deg, transparent, #4a5a6a, transparent);
	}

	.hero-desc {
		font-size: 13px;
		color: #a8b8c8;
		text-align: center;
		line-height: 1.65;
		flex: 1;
	}

	.chosen-badge {
		margin-top: 8px;
		padding: 4px 14px;
		border-radius: 999px;
		background: #26462f;
		border: 1px solid #5f9d69;
		color: #c8ffd4;
		font-size: 11px;
		font-weight: 700;
		letter-spacing: 0.08em;
		text-transform: uppercase;
	}

	@media (max-width: 740px) {
		.cards {
			flex-direction: column;
			align-items: center;
		}
		.hero-card {
			width: min(90vw, 320px);
		}
	}
</style>
