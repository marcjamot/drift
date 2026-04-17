<script lang="ts">
	import { connection } from "$lib/game/connection.svelte.js";
	import { ui } from "$lib/game/ui.svelte.js";

	interface Props {
		onrestart: () => void;
	}
	let { onrestart }: Props = $props();

	function ordinal(n: number): string {
		if (n === 1) return "1st";
		if (n === 2) return "2nd";
		if (n === 3) return "3rd";
		return `${n}th`;
	}

	const placement = $derived(ui.gameOverPlacement);
	const mmrDelta = $derived(ui.gameOverMmrDelta);
</script>

<div class="game-over">
	<div class="go-content">
		{#if placement === 1}
			<div class="go-result win">Victory</div>
			<div class="go-sub">1st place — well played, {connection.playerName}.</div>
		{:else if placement !== null && placement <= 4}
			<div class="go-result win">{ordinal(placement)} Place</div>
			<div class="go-sub">Top 4 finish!</div>
		{:else if placement !== null}
			<div class="go-result loss">{ordinal(placement)} Place</div>
			<div class="go-sub">Better luck next time.</div>
		{:else}
			<div class="go-result">Game over</div>
		{/if}

		{#if mmrDelta !== null}
			<div class="mmr-chip" class:gain={mmrDelta > 0} class:loss={mmrDelta < 0}>
				{mmrDelta > 0 ? `+${mmrDelta}` : mmrDelta} MMR
			</div>
		{/if}

		<button class="btn primary lg" onclick={onrestart}>Play again</button>
	</div>
</div>

<style>
	.game-over {
		height: 100vh;
		display: flex;
		align-items: center;
		justify-content: center;
		animation: go-reveal 0.6s ease-out;
	}
	@keyframes go-reveal {
		from { opacity: 0; }
		to { opacity: 1; }
	}
	.go-content {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 18px;
	}
	.go-result {
		font-size: 64px;
		font-weight: 700;
		letter-spacing: -0.03em;
		color: #f2eadc;
	}
	.go-result.win {
		color: #91d694;
	}
	.go-result.loss {
		color: #df8f8f;
	}
	.go-sub {
		font-size: 15px;
		color: #b5a992;
	}

	.mmr-chip {
		font-size: 22px;
		font-weight: 800;
		padding: 8px 24px;
		border-radius: 999px;
		border: 1px solid #3a4a3a;
		background: #111a11;
		color: #a0c0a0;
	}
	.mmr-chip.gain {
		color: #80e880;
		border-color: #3a6a3a;
		background: #0e1a0e;
		box-shadow: 0 0 20px 2px #80e88022;
	}
	.mmr-chip.loss {
		color: #e88080;
		border-color: #6a3a3a;
		background: #1a0e0e;
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
	.btn.primary {
		background: #6f5632;
		border-color: #b79258;
		color: #fff3da;
	}
	.btn.primary:hover:not(:disabled) {
		background: #81653c;
	}
	.btn.lg {
		font-size: 16px;
		padding: 12px 30px;
	}
</style>
