<script lang="ts">
	import type { MinionSnapshot } from "../game/types.js";
	import MinionCard from "./MinionCard.svelte";

	interface Props {
		minions: MinionSnapshot[];
		label?: string;
		size?: "small" | "medium" | "large";
		cardsDraggable?: boolean;
		align?: "start" | "center";
		emptyLabel?: string;
		selectable?: boolean;
		selectedIndex?: number | null;
		strickenIds?: Set<string>;
		impactIds?: Set<string>;
		attackDirection?: "up" | "down";
		showHealthLeft?: boolean;
		dyingIds?: Set<string>;
		newIds?: Set<string>;
		/** Per-card inline style strings for JS-driven transforms (e.g. lunge). */
		cardStyles?: Map<string, string>;
		/** Strip background/border so cards float directly in a parent arena. */
		bare?: boolean;
		onselect?: (index: number) => void;
		oncarddragstart?: (index: number, event: DragEvent) => void;
		oncarddragend?: (event: DragEvent) => void;
		oncarddragover?: (index: number, event: DragEvent) => void;
		oncarddrop?: (index: number, event: DragEvent) => void;
	}

	let {
		minions,
		label = "",
		size = "medium",
		cardsDraggable = false,
		align = "center",
		emptyLabel = "empty",
		selectable = false,
		selectedIndex = null,
		strickenIds = new Set(),
		impactIds = new Set(),
		attackDirection = "up",
		showHealthLeft = false,
		dyingIds = new Set(),
		newIds = new Set(),
		cardStyles = new Map(),
		bare = false,
		onselect,
		oncarddragstart,
		oncarddragend,
		oncarddragover,
		oncarddrop,
	}: Props = $props();
</script>

<div class="board-wrap">
	{#if label}
		<div class="board-label">{label}</div>
	{/if}
	<div class="board" class:centered={align === "center"} class:bare>
		{#each minions as minion, i (minion.instance_id)}
			<div
				class="card-slot"
				role="group"
				aria-label={`Board slot ${i + 1}`}
				ondragover={oncarddragover ? (event) => oncarddragover(i, event) : undefined}
				ondrop={oncarddrop ? (event) => oncarddrop(i, event) : undefined}
			>
				<MinionCard
					cardId={`card-${minion.instance_id}`}
					{minion}
					{size}
					draggable={cardsDraggable}
					selected={selectedIndex === i}
					stricken={strickenIds.has(minion.instance_id)}
					impact={impactIds.has(minion.instance_id)}
					{attackDirection}
					{showHealthLeft}
					dying={dyingIds.has(minion.instance_id)}
					isNew={newIds.has(minion.instance_id)}
					lungeStyle={cardStyles.get(minion.instance_id) ?? ""}
					onclick={selectable ? () => onselect?.(i) : undefined}
					ondragstart={cardsDraggable ? (event) => oncarddragstart?.(i, event) : undefined}
					ondragend={cardsDraggable ? oncarddragend : undefined}
				/>
			</div>
		{/each}
		{#if minions.length === 0}
			<span class="empty">{emptyLabel}</span>
		{/if}
	</div>
</div>

<style>
	.board-wrap {
		display: flex;
		flex-direction: column;
		gap: 6px;
	}
	.board-label {
		font-size: 10px;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: #444;
	}
	.board {
		display: flex;
		flex-wrap: wrap;
		gap: 14px;
		background: #0c0c18;
		border: 1px solid #1a1a28;
		border-radius: 18px;
		padding: 16px;
		align-items: flex-end;
		align-content: center;
	}
	.board.centered {
		justify-content: center;
	}
	.card-slot {
		position: relative;
		border-radius: 16px;
	}
	/* bare = no panel chrome; cards float directly in the arena */
	.board.bare {
		background: none;
		border: none;
		border-radius: 0;
		padding: 0;
	}
	.empty {
		color: #2a2a3a;
		font-size: 12px;
		align-self: center;
		margin: auto;
		letter-spacing: 0.06em;
	}
</style>
