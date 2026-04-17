<script lang="ts">
	import CardBoard from "$lib/components/CardBoard.svelte";
	import type { MinionSnapshot } from "$lib/game/types.js";

	interface Props {
		minions: MinionSnapshot[];
		strickenIds: Set<string>;
		impactIds: Set<string>;
		dyingIds: Set<string>;
		newIds: Set<string>;
		badgeTextById: Map<string, string>;
		cleaveSplashIds: Set<string>;
		cardStyles: Map<string, string>;
		healthFlash: boolean;
	}

	let { minions, strickenIds, impactIds, dyingIds, newIds, badgeTextById, cleaveSplashIds, cardStyles, healthFlash }: Props = $props();
</script>

<div class="arena-row self-row" class:flash={healthFlash}>
	<CardBoard
		{minions}
		size="large"
		align="center"
		bare={true}
		emptyLabel="No minions"
		{strickenIds}
		{impactIds}
		attackDirection="up"
		{dyingIds}
		{newIds}
		{badgeTextById}
		{cleaveSplashIds}
		{cardStyles}
	/>
</div>

<style>
	.arena-row {
		flex: 1;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 12px 20px;
		overflow: visible;
	}
	.self-row {
		align-items: flex-start;
		padding-top: 6px;
	}
	.self-row.flash {
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
</style>
