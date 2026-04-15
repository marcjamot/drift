<script lang="ts">
	import { gs } from "$lib/game/store.svelte.js";

	interface Props {
		onrestart: () => void;
	}
	let { onrestart }: Props = $props();
</script>

<div class="game-over">
	<div class="go-content">
		{#if gs.gameOverWinner === gs.playerId}
			<div class="go-result win">Victory</div>
			<div class="go-sub">Well played, {gs.playerName}.</div>
		{:else if gs.gameOverWinner}
			<div class="go-result loss">Defeat</div>
			<div class="go-sub">Better luck next time.</div>
		{:else}
			<div class="go-result">Game over</div>
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
		from {
			opacity: 0;
		}
		to {
			opacity: 1;
		}
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
