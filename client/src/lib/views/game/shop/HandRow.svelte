<script lang="ts">
	import CardBoard from "$lib/components/CardBoard.svelte";
	import type { MinionSnapshot } from "$lib/game/types.js";

	interface Props {
		hand: MinionSnapshot[];
		cardsDraggable?: boolean;
		oncarddragstart?: (index: number, event: DragEvent) => void;
		oncarddragend?: (event: DragEvent) => void;
		ghostSourceIds?: Set<string>;
	}

	let { hand, cardsDraggable = false, oncarddragstart, oncarddragend, ghostSourceIds = new Set<string>() }: Props = $props();
</script>

<div class="section-head">
	<div class="section-kicker">Hand</div>
	<span class="meta-pill">Cards {hand.length}</span>
</div>
<CardBoard
	minions={hand}
	size="small"
	align="center"
	emptyLabel="Buy from the shop to build your hand"
	{cardsDraggable}
	{oncarddragstart}
	{oncarddragend}
	{ghostSourceIds}
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
	.meta-pill {
		padding: 6px 12px;
		border-radius: 999px;
		border: 1px solid #37424d;
		background: #171c22;
	}
</style>
