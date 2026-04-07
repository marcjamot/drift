<script lang="ts">
	import type { MinionSnapshot } from '../types.js';

	interface Props {
		minion: MinionSnapshot;
		cardId?: string;
		size?: 'small' | 'medium' | 'large';
		draggable?: boolean;
		selected?: boolean;
		highlighted?: boolean;
		attacking?: boolean;
		targeted?: boolean;
		stricken?: boolean;
		impact?: boolean;
		attackDirection?: 'up' | 'down';
		showHealthLeft?: boolean;
		dying?: boolean;
		isNew?: boolean;
		lungeStyle?: string;
		onclick?: () => void;
		ondragstart?: (event: DragEvent) => void;
		ondragend?: (event: DragEvent) => void;
	}

	let {
		minion,
		cardId = undefined,
		size = 'medium',
		draggable = false,
		selected = false,
		highlighted = false,
		attacking = false,
		targeted = false,
		stricken = false,
		impact = false,
		attackDirection = 'up',
		showHealthLeft = false,
		dying = false,
		isNew = false,
		lungeStyle = '',
		onclick,
		ondragstart,
		ondragend
	}: Props = $props();
</script>

<button
	id={cardId}
	class="minion-card"
	class:size-small={size === 'small'}
	class:size-medium={size === 'medium'}
	class:size-large={size === 'large'}
	class:draggable
	class:selected
	class:taunt={minion.keywords.includes('taunt')}
	class:divine={minion.divine_shield}
	class:highlighted
	class:attacking
	class:targeted
	class:stricken
	class:impact
	class:attack-up={attackDirection === 'up'}
	class:attack-down={attackDirection === 'down'}
	class:dying
	class:is-new={isNew}
	style={lungeStyle}
	{draggable}
	{onclick}
	{ondragstart}
	{ondragend}
	title={minion.name}
>
	{#if showHealthLeft}
		<div class="health-left" class:low={minion.health <= 2}>
			<span class="health-left-label">HP</span>
			<span class="health-left-value">{minion.health}</span>
		</div>
	{/if}
	<div class="name">{minion.name}</div>
	<div class="keywords">
		{#each minion.keywords as kw}
			<span class="keyword">{kw}</span>
		{/each}
		{#if minion.divine_shield}
			<span class="keyword ds">divine</span>
		{/if}
	</div>
	<div class="stats">
		<span class="atk">{minion.attack}</span>
		<span class="sep">/</span>
		<span class="hp" class:damaged={minion.health < minion.max_health}>
			{minion.health}
		</span>
	</div>
	{#if minion.golden}<div class="star">★</div>{/if}
</button>

<style>
	.minion-card {
		position: relative;
		width: 104px;
		min-height: 132px;
		background: #141420;
		border: 2px solid #333;
		border-radius: 14px;
		padding: 10px 8px 8px;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 6px;
		cursor: default;
		font-family: inherit;
		color: #e0e0e0;
		/* transform transition drives the JS-controlled lunge */
		transition:
			border-color 0.15s,
			transform 0.28s cubic-bezier(0.25, 0.46, 0.45, 0.94),
			opacity 0.4s,
			box-shadow 0.2s;
	}

	.minion-card[onclick] {
		cursor: pointer;
	}

	.minion-card.draggable {
		cursor: grab;
	}

	.minion-card.draggable:active {
		cursor: grabbing;
	}

	.minion-card:hover {
		border-color: #666;
		transform: translateY(-3px);
	}

	.minion-card.selected {
		border-color: #d4a020;
		box-shadow: 0 0 10px #d4a02055;
	}
	.minion-card.taunt {
		border-color: #8a6020;
	}
	.minion-card.divine {
		border-color: #6090d0;
		box-shadow: 0 0 8px #6090d033;
	}
	.minion-card.highlighted {
		border-color: #4b88ff;
		box-shadow: 0 0 16px #4b88ff66;
	}

	/* Attacking: glow + elevated z so the card lunges above everything */
	.minion-card.attacking {
		border-color: #4b88ff;
		box-shadow: 0 0 22px #4b88ffaa;
		z-index: 20;
		/* fast transition when lunging so it snaps to target quickly */
		transition:
			border-color 0.15s,
			transform 0.26s cubic-bezier(0.25, 0.46, 0.45, 0.94),
			box-shadow 0.2s;
	}

	.minion-card.targeted {
		border-color: #d35b5b;
		border-style: dashed;
		box-shadow: 0 0 10px #d35b5b55;
	}

	/* Shake when struck */
	.minion-card.stricken {
		animation: struck-shake 0.38s ease-in-out;
	}

	/* Orange hit flash on the card that receives the blow */
	.minion-card.impact {
		animation: impact-flash 0.38s ease-out;
	}

	.minion-card.dying {
		opacity: 0;
		transform: scale(0.7) translateY(10px);
		pointer-events: none;
	}

	.minion-card.is-new {
		animation: pop-in 0.35s cubic-bezier(0.34, 1.56, 0.64, 1) both;
	}

	@keyframes pop-in {
		from {
			opacity: 0;
			transform: scale(0.5) translateY(20px);
		}
		to {
			opacity: 1;
			transform: scale(1) translateY(0);
		}
	}

	@keyframes struck-shake {
		0%   { transform: translateX(0); }
		18%  { transform: translateX(-7px); }
		36%  { transform: translateX(7px); }
		54%  { transform: translateX(-5px); }
		72%  { transform: translateX(5px); }
		100% { transform: translateX(0); }
	}

	@keyframes impact-flash {
		0%   { box-shadow: 0 0 0   0   transparent; filter: brightness(1); }
		22%  { box-shadow: 0 0 32px 10px #ff8c3099; filter: brightness(1.6); }
		100% { box-shadow: none;                    filter: brightness(1); }
	}

	.minion-card.size-small {
		width: 86px;
		min-height: 108px;
		border-radius: 10px;
		padding: 8px 6px 6px;
		gap: 4px;
	}

	.minion-card.size-large {
		width: 136px;
		min-height: 172px;
		border-radius: 18px;
		padding: 12px 10px 10px;
		gap: 8px;
	}

	.name {
		font-size: 13px;
		font-weight: 600;
		text-align: center;
		line-height: 1.2;
		color: #bbb;
		word-break: break-word;
	}
	.minion-card.size-small .name {
		font-size: 11px;
	}
	.minion-card.size-large .name {
		font-size: 16px;
	}
	.keywords {
		display: flex;
		flex-wrap: wrap;
		justify-content: center;
		gap: 4px;
	}
	.keyword {
		font-size: 9px;
		background: #222;
		border-radius: 999px;
		padding: 2px 6px;
		color: #999;
		text-transform: uppercase;
		letter-spacing: 0.04em;
	}
	.minion-card.size-small .keyword {
		font-size: 8px;
		padding: 1px 5px;
	}
	.minion-card.size-large .keyword {
		font-size: 10px;
		padding: 3px 7px;
	}
	.ds {
		color: #6090d0;
	}
	.stats {
		font-size: 24px;
		font-weight: 700;
		margin-top: auto;
		letter-spacing: -0.02em;
	}
	.minion-card.size-small .stats {
		font-size: 19px;
	}
	.minion-card.size-large .stats {
		font-size: 30px;
	}
	.atk {
		color: #e08050;
	}
	.sep {
		color: #444;
	}
	.hp {
		color: #50c050;
	}
	.hp.damaged {
		color: #c04040;
	}
	.star {
		position: absolute;
		top: 6px;
		right: 8px;
		font-size: 14px;
		color: #d4a020;
	}
	.minion-card.size-small .star {
		font-size: 11px;
		top: 4px;
		right: 6px;
	}
	.health-left {
		position: absolute;
		top: 8px;
		left: 50%;
		transform: translateX(-50%);
		display: flex;
		align-items: center;
		gap: 4px;
		font-size: 12px;
		font-weight: 700;
		line-height: 1;
		padding: 4px 8px;
		border-radius: 999px;
		background: #10291a;
		border: 1px solid #3f8a56;
		color: #c9ffd6;
		box-shadow: 0 2px 10px #00000055;
		z-index: 3;
		white-space: nowrap;
	}
	.minion-card.size-small .health-left {
		font-size: 10px;
		padding: 3px 6px;
	}
	.health-left.low {
		background: #341515;
		border-color: #b04d4d;
		color: #ffd0d0;
	}
	.health-left-label {
		font-size: 8px;
		letter-spacing: 0.08em;
		color: #8bbd98;
	}
	.health-left.low .health-left-label {
		color: #dba2a2;
	}
	.health-left-value {
		font-size: 11px;
		font-weight: 800;
	}
</style>
