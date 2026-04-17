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
		targeting?: boolean;
		ontargetselect?: (index: number) => void;
	}

	let { self, cardsDraggable = false, oncarddragstart, oncarddragend, ghostSourceShopIndex = null, targeting = false, ontargetselect }: Props = $props();
</script>

<div class="shop-content">
	<div class="shop-row">
		{#each self.shop as slot, i (`${slot?.instance_id ?? "empty"}-${i}`)}
			{#if slot}
				<!-- svelte-ignore a11y_click_events_have_key_events -->
				<div
					class="shop-slot"
					class:target-highlight={targeting}
					role={targeting ? "button" : undefined}
					onclick={targeting ? () => ontargetselect?.(i) : undefined}
				>
					<MinionCard
						minion={slot}
						size="large"
						draggable={cardsDraggable && !targeting}
						ghostSource={ghostSourceShopIndex === i}
						ondragstart={cardsDraggable && !targeting ? (event) => oncarddragstart?.(i, slot, event) : undefined}
						ondragend={cardsDraggable && !targeting ? oncarddragend : undefined}
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
		border-radius: 18px;
		transition: box-shadow 0.15s, transform 0.15s;
	}
	.shop-slot.target-highlight {
		cursor: pointer;
		box-shadow: 0 0 0 2px #7ab0e088, 0 0 16px 4px #3a6ab033;
		transform: translateY(-2px);
	}
	.shop-slot.target-highlight:hover {
		box-shadow: 0 0 0 2px #a8d4ff, 0 0 24px 6px #5a8abf44;
		transform: translateY(-4px);
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
