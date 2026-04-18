<script lang="ts">
	import { send } from "$lib/game/connection.svelte.js";
	import { ui } from "$lib/game/ui.svelte.js";
</script>

<div class="splash">
	<h1 class="wordmark">drift</h1>
	<p class="waiting">Looking for players</p>
	<p class="count">{ui.queuedCount} / {ui.totalSlots} players found</p>
	{#if ui.queueSecondsLeft !== null}
		<p class="timer">Filling with bots in {ui.queueSecondsLeft}s</p>
	{/if}
	{#if ui.canSkipQueueWait}
		<button class="skip" type="button" onclick={() => send({ type: "queue_now" })}>
			Play with bots now
		</button>
	{/if}
	<div class="dots"><span></span><span></span><span></span></div>
</div>

<style>
	.splash {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		height: 100vh;
		gap: 20px;
	}
	.wordmark {
		font-size: clamp(56px, 12vw, 90px);
		font-weight: 700;
		letter-spacing: -0.05em;
		color: #f4ecdf;
	}
	.waiting {
		color: #b5a992;
	}
	.count {
		font-size: 18px;
		color: #f4ecdf;
	}
	.timer {
		color: #9db8c7;
	}
	.skip {
		border: 1px solid #8f7853;
		border-radius: 8px;
		background: #d1a84f;
		color: #18110a;
		padding: 10px 16px;
		font: inherit;
		cursor: pointer;
	}
	.skip:hover {
		background: #e1bb62;
	}
	.dots {
		display: flex;
		gap: 6px;
	}
	.dots span {
		width: 7px;
		height: 7px;
		border-radius: 50%;
		background: #6b624f;
		animation: pulse 1.2s ease-in-out infinite;
	}
	.dots span:nth-child(2) {
		animation-delay: 0.2s;
	}
	.dots span:nth-child(3) {
		animation-delay: 0.4s;
	}
	@keyframes pulse {
		0%,
		80%,
		100% {
			opacity: 0.35;
		}
		40% {
			opacity: 1;
		}
	}
</style>
