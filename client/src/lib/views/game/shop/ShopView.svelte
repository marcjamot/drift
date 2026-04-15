<script lang="ts">
	import { gs, send } from "$lib/game/store.svelte.js";
	import type { MinionSnapshot } from "$lib/game/types.js";
	import ShopRow from "./ShopRow.svelte";
	import HandRow from "./HandRow.svelte";
	import BoardRow from "./BoardRow.svelte";

	interface Props {
		healthFlash: boolean;
	}
	let { healthFlash }: Props = $props();

	const BUY_COST = 3;
	const HAND_LIMIT = 10;
	const BOARD_LIMIT = 7;

	let activeDropZone = $state<"shop" | "board" | "hand" | null>(null);
	let boardDropTargetIndex = $state<number | null>(null);
	let dragSource = $state<{
		origin: "shop" | "board" | "hand";
		index: number;
		name: string;
	} | null>(null);

	let newBoardIds = $state(new Set<string>());
	let prevBoardIds = new Set<string>();

	$effect(() => {
		if (!gs.self) return;
		const ids = gs.self.board.map((m) => m.instance_id);
		const added = ids.filter((id) => !prevBoardIds.has(id));
		prevBoardIds = new Set(ids);
		if (added.length === 0) return;
		newBoardIds = new Set(added);
		setTimeout(() => (newBoardIds = new Set()), 500);
	});

	$effect(() => {
		if (gs.phase !== "buy") clearDragState();
	});

	function clearDragState() {
		activeDropZone = null;
		boardDropTargetIndex = null;
		dragSource = null;
	}

	function isHandFull() {
		return !!gs.self && gs.self.hand.length >= HAND_LIMIT;
	}

	function isBoardFull() {
		return !!gs.self && gs.self.board.length >= BOARD_LIMIT;
	}

	function getDropStatus(zone: "shop" | "board" | "hand") {
		if (!dragSource || !gs.self) return null;

		if (zone === "shop") {
			if (dragSource.origin === "board") return { valid: true, title: "Sell to shop", detail: "Gain 1 gold" };
			return null;
		}

		if (zone === "hand") {
			if (dragSource.origin !== "shop") return null;
			if (isHandFull()) return null;
			if (gs.self.gold < BUY_COST) return null;
			return { valid: true, title: "Buy to hand", detail: `${dragSource.name} will be added to hand` };
		}

		// zone === "board"
		if (dragSource.origin === "board") return null;
		if (dragSource.origin === "hand") {
			if (isBoardFull()) return null;
			return { valid: true, title: "Play to board", detail: `${dragSource.name} will be played from hand` };
		}
		if (dragSource.origin === "shop") {
			if (isHandFull()) return null;
			if (gs.self.gold < BUY_COST) return null;
			return { valid: true, title: "Buy to hand", detail: `${dragSource.name} will be bought into hand` };
		}
		return null;
	}

	function canDrop(zone: "shop" | "board" | "hand") {
		if (!dragSource || !gs.self) return false;
		if (zone === "shop") return dragSource.origin === "board";
		if (zone === "hand") return dragSource.origin === "shop" && !isHandFull() && gs.self.gold >= BUY_COST;
		if (dragSource.origin === "hand") return !isBoardFull();
		if (dragSource.origin === "shop") return !isHandFull() && gs.self.gold >= BUY_COST;
		return false;
	}

	function getBoardPreview() {
		if (!gs.self) return [];
		if (!dragSource || dragSource.origin !== "board") return gs.self.board;
		if (boardDropTargetIndex === null || boardDropTargetIndex === dragSource.index) return gs.self.board;
		const preview = [...gs.self.board];
		const [moved] = preview.splice(dragSource.index, 1);
		preview.splice(Math.min(boardDropTargetIndex, preview.length), 0, moved);
		return preview;
	}

	function dragOverZone(zone: "shop" | "board" | "hand", event: DragEvent) {
		if (!dragSource) return;
		if (!canDrop(zone) && !(zone === "board" && dragSource.origin === "board")) return;
		event.preventDefault();
		activeDropZone = zone;
		if (zone !== "board") boardDropTargetIndex = null;
	}

	function dragEnterZone(zone: "shop" | "board" | "hand") {
		if (!dragSource) return;
		if (!canDrop(zone) && !(zone === "board" && dragSource.origin === "board")) return;
		activeDropZone = zone;
		if (zone !== "board") boardDropTargetIndex = null;
	}

	function dropOnZone(zone: "shop" | "board" | "hand", event: DragEvent) {
		event.preventDefault();
		if (!dragSource) return;
		const source = dragSource;

		if (zone === "board" && source.origin === "board") {
			const targetIndex = boardDropTargetIndex;
			clearDragState();
			if (targetIndex === null || targetIndex === source.index) return;
			send({ type: "reorder", from_index: source.index, to_index: targetIndex });
			return;
		}

		const status = getDropStatus(zone);
		clearDragState();
		if (!status?.valid) return;

		if (zone === "shop" && source.origin === "board") {
			send({ type: "sell", board_index: source.index });
			return;
		}
		if (zone === "board" && source.origin === "hand") {
			send({ type: "play", hand_index: source.index });
			return;
		}
		if ((zone === "board" || zone === "hand") && source.origin === "shop") {
			send({ type: "buy", shop_index: source.index });
		}
	}

	function dragShopCard(index: number, minion: MinionSnapshot, event: DragEvent) {
		if (gs.phase !== "buy") return;
		event.dataTransfer?.setData("text/plain", `shop:${index}`);
		if (event.dataTransfer) event.dataTransfer.effectAllowed = "move";
		dragSource = { origin: "shop", index, name: minion.name };
		activeDropZone = null;
	}

	function dragHandCard(index: number, event: DragEvent) {
		if (gs.phase !== "buy" || !gs.self) return;
		const minion = gs.self.hand[index];
		if (!minion) return;
		event.dataTransfer?.setData("text/plain", `hand:${index}`);
		if (event.dataTransfer) event.dataTransfer.effectAllowed = "move";
		dragSource = { origin: "hand", index, name: minion.name };
		activeDropZone = null;
	}

	function dragBoardCard(index: number, event: DragEvent) {
		if (gs.phase !== "buy" || !gs.self) return;
		const minion = gs.self.board[index];
		if (!minion) return;
		event.dataTransfer?.setData("text/plain", `board:${index}`);
		if (event.dataTransfer) event.dataTransfer.effectAllowed = "move";
		dragSource = { origin: "board", index, name: minion.name };
		activeDropZone = null;
	}

	function dragEnded() {
		clearDragState();
	}

	function dragOverBoardCard(index: number, event: DragEvent) {
		if (!dragSource || dragSource.origin !== "board") return;
		event.preventDefault();
		activeDropZone = "board";
		boardDropTargetIndex = index;
	}

	function dropOnBoardCard(index: number, event: DragEvent) {
		event.preventDefault();
		if (!dragSource) return;
		const source = dragSource;
		const shouldReorder = source.origin === "board" && source.index !== index;
		clearDragState();
		if (!shouldReorder) return;
		send({ type: "reorder", from_index: source.index, to_index: index });
	}
</script>

{#if gs.self}
	<div class="buy-layout" class:flash={healthFlash}>
		<!-- Shop panel: cards available to purchase -->
		<section
			class="panel shop-panel drop-zone"
			role="group"
			aria-label="Shop drop zone"
			class:dragging={!!dragSource}
			class:active={activeDropZone === "shop"}
			class:valid={!!getDropStatus("shop")}
			ondragover={(event) => dragOverZone("shop", event)}
			ondragenter={() => dragEnterZone("shop")}
			ondrop={(event) => dropOnZone("shop", event)}
		>
			<ShopRow
				self={gs.self}
				cardsDraggable={true}
				oncarddragstart={dragShopCard}
				oncarddragend={dragEnded}
			/>
			{#if getDropStatus("shop")}
				<div class="drop-overlay">
					<div class="drop-title">{getDropStatus("shop")?.title}</div>
					<div class="drop-detail">{getDropStatus("shop")?.detail}</div>
				</div>
			{/if}
		</section>

		<!-- Board panel: cards in play (enter combat, sellable) -->
		<section
			class="panel board-panel drop-zone"
			role="group"
			aria-label="Board drop zone"
			class:dragging={!!dragSource}
			class:active={activeDropZone === "board"}
			class:valid={!!getDropStatus("board")}
			ondragover={(event) => dragOverZone("board", event)}
			ondragenter={() => dragEnterZone("board")}
			ondrop={(event) => dropOnZone("board", event)}
		>
			<BoardRow
				self={gs.self}
				boardPreview={getBoardPreview()}
				newIds={newBoardIds}
				cardsDraggable={true}
				oncarddragstart={dragBoardCard}
				oncarddragend={dragEnded}
				oncarddragover={dragOverBoardCard}
				oncarddrop={dropOnBoardCard}
			/>
			{#if getDropStatus("board")}
				<div class="drop-overlay">
					<div class="drop-title">{getDropStatus("board")?.title}</div>
					<div class="drop-detail">{getDropStatus("board")?.detail}</div>
				</div>
			{/if}
		</section>

		<!-- Hand panel: purchased but not yet played -->
		<section
			class="panel hand-panel drop-zone"
			role="group"
			aria-label="Hand drop zone"
			class:dragging={!!dragSource}
			class:active={activeDropZone === "hand"}
			class:valid={!!getDropStatus("hand")}
			ondragover={(event) => dragOverZone("hand", event)}
			ondragenter={() => dragEnterZone("hand")}
			ondrop={(event) => dropOnZone("hand", event)}
		>
			<HandRow
				hand={gs.self.hand}
				cardsDraggable={true}
				oncarddragstart={dragHandCard}
				oncarddragend={dragEnded}
			/>
			{#if getDropStatus("hand")}
				<div class="drop-overlay">
					<div class="drop-title">{getDropStatus("hand")?.title}</div>
					<div class="drop-detail">{getDropStatus("hand")?.detail}</div>
				</div>
			{/if}
		</section>
	</div>
{/if}

<style>
	.buy-layout {
		display: flex;
		flex-direction: column;
		gap: 18px;
		flex: 1;
		min-height: 0;
		overflow-y: auto;
		padding-right: 4px;
	}
	.buy-layout.flash {
		animation: dmg-flash 0.8s ease-out;
	}
	@keyframes dmg-flash {
		0% {
			filter: brightness(1.18) saturate(1.2);
		}
		100% {
			filter: none;
		}
	}

	.panel {
		position: relative;
		border-radius: 24px;
		background: rgba(12, 15, 19, 0.82);
		border: 1px solid #2f3944;
		backdrop-filter: blur(8px);
		padding: 20px;
		display: flex;
		flex-direction: column;
		gap: 16px;
		flex-shrink: 0;
	}
	.shop-panel {
		align-items: center;
	}
	.board-panel {
		min-height: 220px;
	}
	.hand-panel {
		min-height: 160px;
	}

	.drop-zone.dragging {
		transition:
			border-color 0.15s,
			box-shadow 0.15s,
			background 0.15s;
	}
	.drop-zone.dragging.valid {
		border-color: #4d8b5f;
		box-shadow: inset 0 0 0 1px #4d8b5f55;
	}
	.drop-zone.dragging.active.valid {
		background: rgba(14, 34, 18, 0.9);
		box-shadow:
			inset 0 0 0 1px #71c18699,
			0 0 0 1px #71c18644;
	}

	.drop-overlay {
		position: absolute;
		inset: 12px;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 6px;
		padding: 16px;
		border-radius: 18px;
		background: rgba(9, 11, 15, 0.82);
		border: 1px dashed #485463;
		backdrop-filter: blur(6px);
		pointer-events: none;
		text-align: center;
		z-index: 5;
	}
	.drop-zone.valid .drop-overlay {
		border-color: #71c186;
		color: #d8ffdf;
	}
	.drop-title {
		font-size: 15px;
		font-weight: 700;
		letter-spacing: 0.02em;
	}
	.drop-detail {
		font-size: 12px;
		color: #c4cdd8;
		max-width: 28ch;
	}

	@media (max-width: 900px) {
		.buy-layout {
			gap: 12px;
		}
		.panel {
			padding: 14px;
		}
	}
</style>
