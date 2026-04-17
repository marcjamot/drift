<script lang="ts">
	import { send } from "$lib/game/store.svelte.js";
	import type { MinionSnapshot } from "$lib/game/types.js";
	import MinionCard from "./MinionCard.svelte";

	interface Props {
		options: MinionSnapshot[];
	}
	let { options }: Props = $props();

	function pick(index: number) {
		send({ type: "discover_pick", index });
	}
</script>

<div class="discover-overlay" role="dialog" aria-modal="true" aria-label="Discover a minion">
	<div class="discover-panel">
		<h2 class="discover-title">Discover a Minion</h2>
		<p class="discover-subtitle">Choose one to add to your hand</p>
		<div class="discover-cards">
			{#each options as option, i (option.instance_id)}
				<button class="discover-card-wrap" onclick={() => pick(i)}>
					<MinionCard minion={option} size="large" />
				</button>
			{/each}
		</div>
	</div>
</div>

<style>
	.discover-overlay {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.72);
		backdrop-filter: blur(6px);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 200;
		animation: fade-in 0.18s ease-out both;
	}

	@keyframes fade-in {
		from { opacity: 0; }
		to { opacity: 1; }
	}

	.discover-panel {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 24px;
		background: rgba(12, 15, 22, 0.96);
		border: 1px solid #3a4455;
		border-radius: 28px;
		padding: 36px 40px;
		box-shadow: 0 32px 80px #000000bb;
		animation: panel-in 0.22s cubic-bezier(0.22, 1, 0.36, 1) both;
	}

	@keyframes panel-in {
		from { opacity: 0; transform: scale(0.88) translateY(16px); }
		to { opacity: 1; transform: scale(1) translateY(0); }
	}

	.discover-title {
		margin: 0;
		font-size: 22px;
		font-weight: 700;
		color: #d4a020;
		letter-spacing: 0.02em;
	}

	.discover-subtitle {
		margin: -16px 0 0;
		font-size: 13px;
		color: #8899aa;
	}

	.discover-cards {
		display: flex;
		gap: 20px;
		flex-wrap: wrap;
		justify-content: center;
	}

	.discover-card-wrap {
		background: none;
		border: none;
		padding: 0;
		cursor: pointer;
		border-radius: 18px;
		transition: transform 0.15s cubic-bezier(0.22, 1, 0.36, 1), box-shadow 0.15s;
	}

	.discover-card-wrap:hover {
		transform: translateY(-6px) scale(1.04);
		box-shadow: 0 16px 40px #000000aa, 0 0 0 2px #d4a02077;
	}

	.discover-card-wrap:focus-visible {
		outline: 2px solid #d4a020;
		outline-offset: 4px;
	}
</style>
