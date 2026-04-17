<script lang="ts">
	import type { HeroSnapshot } from "$lib/game/types.js";

	interface Props {
		name: string;
		health: number;
		hero: HeroSnapshot | null;
	}
	let { name, health, hero }: Props = $props();
</script>

<div class="self-plate">
	{#if hero}
		<div class="hero-row">
			<span class="hero-name">⚔ {hero.name}</span>
			<span class="hero-sep">·</span>
			<span class="hero-desc">{hero.description}</span>
		</div>
	{/if}
	<div class="arena-nameplate">
		<span class="arena-kicker">You</span>
		<span class="arena-name">{name}</span>
		<span class="arena-hp" class:low={health <= 15}>♥ {health}</span>
	</div>
</div>

<style>
	.self-plate {
		border-top: 1px solid #2a2218;
	}
	.arena-nameplate {
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 6px 20px 10px;
	}
	.arena-kicker {
		font-size: 10px;
		letter-spacing: 0.14em;
		text-transform: uppercase;
		color: #6b6050;
	}
	.arena-name {
		font-size: 15px;
		font-weight: 700;
		color: #d4c9b4;
	}
	.arena-hp {
		font-size: 13px;
		color: #7ab87d;
		margin-left: auto;
	}
	.arena-hp.low {
		color: #c46060;
	}
	.hero-row {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 10px 20px 0;
		flex-wrap: wrap;
	}
	.hero-name {
		font-size: 11px;
		font-weight: 700;
		color: #7ab8a0;
		white-space: nowrap;
	}
	.hero-sep {
		font-size: 11px;
		color: #3a3228;
	}
	.hero-desc {
		font-size: 11px;
		color: #4e6a5e;
		line-height: 1.4;
	}
</style>
