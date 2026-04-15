<script lang="ts">
	import type { MinionSnapshot, SelfSnapshot } from "$lib/game/types.js";
	import MinionCard from "$lib/components/MinionCard.svelte";
	import { send } from "$lib/game/store.svelte.js";

	interface Props {
		self: SelfSnapshot;
		cardsDraggable?: boolean;
		oncarddragstart?: (index: number, minion: MinionSnapshot, event: DragEvent) => void;
		oncarddragend?: (event: DragEvent) => void;
		ghostSourceShopIndex?: number | null;
	}

	let { self, cardsDraggable = false, oncarddragstart, oncarddragend, ghostSourceShopIndex = null }: Props = $props();
</script>

<div class="shop-content">
	<div class="shop-row">
		{#each self.shop as slot, i (`${slot?.instance_id ?? "empty"}-${i}`)}
			{#if slot}
				<div class="shop-slot">
					<MinionCard
						minion={slot}
						size="large"
						draggable={cardsDraggable}
						ghostSource={ghostSourceShopIndex === i}
						ondragstart={cardsDraggable ? (event) => oncarddragstart?.(i, slot, event) : undefined}
						ondragend={cardsDraggable ? oncarddragend : undefined}
					/>
					<div class="buy-cost">3g</div>
				</div>
			{:else}
				<div class="shop-slot empty-slot"></div>
			{/if}
		{/each}
	</div>

	<div class="shop-actions">
		<button onclick={() => send({ type: "refresh" })} disabled={self.gold < 1} class="btn">
			Refresh (1g)
		</button>

		{#if self.tavern_tier < 6}
			<button
				onclick={() => send({ type: "upgrade" })}
				disabled={self.gold < self.upgrade_cost}
				class="btn upgrade"
			>
				Upgrade ({self.upgrade_cost}g → Tier {self.tavern_tier + 1})
			</button>
		{:else}
			<span class="max-tier">Max tier</span>
		{/if}

		<button onclick={() => send({ type: "freeze" })} class="btn" class:frozen={self.frozen}>
			{self.frozen ? "❄ Frozen" : "Freeze"}
		</button>
	</div>
</div>

<style>
	.shop-content {
		display: flex;
		flex-direction: column;
		gap: 18px;
		align-items: center;
		width: 100%;
	}
	.shop-row {
		display: flex;
		gap: 16px;
		flex-wrap: wrap;
		justify-content: center;
	}
	.shop-slot {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 2px;
	}
	.empty-slot {
		width: 140px;
		height: 176px;
		border: 2px dashed #2a2a3a;
		border-radius: 18px;
	}
	.buy-cost {
		font-size: 12px;
		font-weight: 700;
		color: #f0c040;
	}
	.shop-actions {
		display: flex;
		gap: 10px;
		flex-wrap: wrap;
		justify-content: center;
	}
	.max-tier {
		font-size: 12px;
		color: #888;
		align-self: center;
	}
	.btn {
		font-family: inherit;
		font-size: 12px;
		padding: 5px 12px;
		border-radius: 5px;
		border: 1px solid #444;
		background: #1e1e2e;
		color: #ccc;
		cursor: pointer;
		transition:
			background 0.1s,
			border-color 0.1s;
	}
	.btn:hover:not(:disabled) {
		background: #2a2a3a;
		border-color: #888;
	}
	.btn:disabled {
		opacity: 0.4;
		cursor: default;
	}
	.btn.upgrade {
		border-color: #60a060;
		color: #80d080;
	}
	.btn.frozen {
		border-color: #80c0ff;
		color: #80c0ff;
	}
</style>
