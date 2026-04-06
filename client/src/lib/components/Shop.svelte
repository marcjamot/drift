<script lang="ts">
	import type { MinionSnapshot } from '../types.js';
	import type { SelfSnapshot } from '../types.js';
	import MinionCard from './MinionCard.svelte';
	import { send } from '../gameStore.svelte.js';

	interface Props {
		self: SelfSnapshot;
	}

	let { self }: Props = $props();

	function buy(idx: number) {
		send({ type: 'buy', shop_index: idx });
	}

	function refresh() {
		send({ type: 'refresh' });
	}

	function freeze() {
		send({ type: 'freeze' });
	}

	function upgrade() {
		send({ type: 'upgrade' });
	}
</script>

<div class="shop-wrap">
	<div class="shop-header">
		<span class="tier-badge">Tier {self.tavern_tier}</span>
		<span class="gold">⬡ {self.gold} / {self.max_gold}</span>
		<span class="hand-count">Hand {self.hand.length}</span>
	</div>

	<div class="shop-row">
		{#each self.shop as slot, i}
			{#if slot}
				<div class="shop-slot">
					<MinionCard minion={slot} size="large" onclick={() => buy(i)} />
					<div class="buy-cost">3g</div>
				</div>
			{:else}
				<div class="shop-slot empty-slot"></div>
			{/if}
		{/each}
	</div>

	<div class="shop-actions">
		<button onclick={refresh} disabled={self.gold < 1} class="btn">
			Refresh (1g)
		</button>

		{#if self.tavern_tier < 6}
			<button onclick={upgrade} disabled={self.gold < self.upgrade_cost} class="btn upgrade">
				Upgrade ({self.upgrade_cost}g → Tier {self.tavern_tier + 1})
			</button>
		{:else}
			<span class="max-tier">Max tier</span>
		{/if}

		<button onclick={freeze} class="btn" class:frozen={self.frozen}>
			{self.frozen ? '❄ Frozen' : 'Freeze'}
		</button>
	</div>
</div>

<style>
	.shop-wrap {
		display: flex;
		flex-direction: column;
		gap: 18px;
		align-items: center;
	}
	.shop-header {
		display: flex;
		align-items: center;
		gap: 12px;
		flex-wrap: wrap;
		justify-content: center;
	}
	.tier-badge {
		font-size: 12px;
		background: #2a2a3a;
		border: 1px solid #444;
		border-radius: 4px;
		padding: 2px 8px;
		color: #ccc;
	}
	.gold {
		font-size: 14px;
		font-weight: 700;
		color: #f0c040;
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
	.hand-count {
		font-size: 12px;
		color: #c9c3a2;
		background: #17141b;
		border: 1px solid #393146;
		border-radius: 999px;
		padding: 4px 10px;
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
		transition: background 0.1s, border-color 0.1s;
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
	.max-tier {
		font-size: 12px;
		color: #888;
		align-self: center;
	}
</style>
