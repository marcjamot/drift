<script lang="ts">
	import CardBoard from "$lib/components/CardBoard.svelte";
	import type { MinionSnapshot, SelfSnapshot } from "$lib/game/types.js";

	interface Props {
		self: SelfSnapshot;
		boardPreview: MinionSnapshot[];
		newIds: Set<string>;
		cardsDraggable?: boolean;
		oncarddragstart?: (index: number, event: DragEvent) => void;
		oncarddragend?: (event: DragEvent) => void;
		oncarddragover?: (index: number, event: DragEvent) => void;
		oncarddrop?: (index: number, event: DragEvent) => void;
	}

	let {
		self,
		boardPreview,
		newIds,
		cardsDraggable = false,
		oncarddragstart,
		oncarddragend,
		oncarddragover,
		oncarddrop,
	}: Props = $props();
</script>

<div class="section-head">
	<div class="section-kicker">Board</div>
	<div class="meta-row">
		<span class="meta-pill">Tier {self.tavern_tier}</span>
		<span class="meta-pill gold">⬡ {self.gold}/{self.max_gold}</span>
	</div>
</div>
<CardBoard
	minions={boardPreview}
	size="medium"
	align="center"
	emptyLabel="Play minions from your hand"
	{cardsDraggable}
	{newIds}
	{oncarddragstart}
	{oncarddragend}
	{oncarddragover}
	{oncarddrop}
/>

<style>
	.section-head {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 12px;
		flex-wrap: wrap;
	}
	.section-kicker {
		font-size: 11px;
		letter-spacing: 0.14em;
		text-transform: uppercase;
		color: #b5a992;
	}
	.meta-row {
		display: flex;
		align-items: center;
		gap: 10px;
		flex-wrap: wrap;
	}
	.meta-pill {
		padding: 6px 12px;
		border-radius: 999px;
		border: 1px solid #37424d;
		background: #171c22;
	}
	.meta-pill.gold {
		color: #ffd87a;
		border-color: #7f6330;
	}
</style>
