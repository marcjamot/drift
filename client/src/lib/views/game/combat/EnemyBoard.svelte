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
	}

	let { minions, strickenIds, impactIds, dyingIds, newIds, badgeTextById, cleaveSplashIds, cardStyles }: Props = $props();
</script>

<div class="arena-row opp-row">
	<CardBoard
		{minions}
		size="large"
		align="center"
		bare={true}
		emptyLabel="No minions"
		{strickenIds}
		{impactIds}
		attackDirection="down"
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
	.opp-row {
		align-items: flex-end;
		padding-bottom: 6px;
	}
</style>
