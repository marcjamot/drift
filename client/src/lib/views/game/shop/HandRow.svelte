<script lang="ts">
	import CardBoard from "$lib/components/CardBoard.svelte";
	import type { MinionSnapshot } from "$lib/game/types.js";

	interface Props {
		hand: MinionSnapshot[];
		cardsDraggable?: boolean;
		oncarddragstart?: (index: number, event: DragEvent) => void;
		oncarddragend?: (event: DragEvent) => void;
		ghostSourceIds?: Set<string>;
		targeting?: boolean;
		ontargetselect?: (index: number) => void;
	}

	let { hand, cardsDraggable = false, oncarddragstart, oncarddragend, ghostSourceIds = new Set<string>(), targeting = false, ontargetselect }: Props = $props();
</script>

<div class="section-head">
	<div class="section-kicker">Hand</div>
	<span class="meta-pill">Cards {hand.length}</span>
</div>
<div class="hand-wrap" class:targeting>
	<CardBoard
		minions={hand}
		size="small"
		align="center"
		emptyLabel="Buy from the shop to build your hand"
		cardsDraggable={cardsDraggable && !targeting}
		{oncarddragstart}
		{oncarddragend}
		{ghostSourceIds}
		selectable={targeting}
		onselect={ontargetselect}
	/>
</div>

<style>
	.hand-wrap {
		width: 100%;
	}
	.hand-wrap.targeting :global(.card-slot) {
		cursor: pointer;
		border-radius: 16px;
		box-shadow: 0 0 0 2px #7ab0e088, 0 0 16px 4px #3a6ab033;
		transform: translateY(-2px);
		transition: box-shadow 0.15s, transform 0.15s;
	}
	.hand-wrap.targeting :global(.card-slot:hover) {
		box-shadow: 0 0 0 2px #a8d4ff, 0 0 24px 6px #5a8abf44;
		transform: translateY(-4px);
	}
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
