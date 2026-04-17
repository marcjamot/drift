<script lang="ts">
	import { gs } from "$lib/game/store.svelte.js";
	import type { LeaderboardEntry } from "$lib/game/types.js";

	function ordinal(n: number): string {
		if (n === 1) return "1st";
		if (n === 2) return "2nd";
		if (n === 3) return "3rd";
		return `${n}th`;
	}

	function isMyOpponent(entry: LeaderboardEntry): boolean {
		return gs.opponent?.player_id === entry.player_id;
	}
</script>

<aside class="leaderboard">
	<div class="lb-header">Players</div>
	{#each gs.leaderboard as entry, i (entry.player_id)}
		{@const isSelf = entry.player_id === gs.playerId}
		{@const isOpponent = isMyOpponent(entry)}
		{@const isDead = entry.health <= 0}
		<div
			class="lb-row"
			class:self={isSelf}
			class:opponent={isOpponent && !isSelf}
			class:dead={isDead}
		>
			<div class="lb-rank">{ordinal(i + 1)}</div>
			<div class="lb-info">
				<div class="lb-name" title={entry.name}>
					{entry.name}
					{#if isSelf}<span class="tag you">you</span>{/if}
					{#if isOpponent && !isSelf}<span class="tag vs">vs</span>{/if}
					{#if entry.is_bot}<span class="tag bot">bot</span>{/if}
				</div>
				<div class="lb-hp" class:low={entry.health <= 15 && !isDead}>
					{#if isDead}
						<span class="dead-label">eliminated</span>
					{:else}
						♥ {entry.health}
					{/if}
				</div>
			</div>
			{#if entry.last_combat_board.length > 0}
				<div class="lb-board">
					{#each entry.last_combat_board as minion (minion.instance_id)}
						<div
							class="lb-minion"
							class:golden={minion.golden}
							title="{minion.name} {minion.attack}/{minion.health}"
						>
							<span class="lb-atk">{minion.attack}</span>
							<span class="lb-hp-mini">{minion.health}</span>
						</div>
					{/each}
				</div>
			{/if}
		</div>
	{/each}
</aside>

<style>
	.leaderboard {
		width: 200px;
		flex-shrink: 0;
		display: flex;
		flex-direction: column;
		gap: 4px;
		overflow-y: auto;
		scrollbar-width: none;
	}
	.leaderboard::-webkit-scrollbar {
		display: none;
	}

	.lb-header {
		font-size: 10px;
		font-weight: 700;
		letter-spacing: 0.1em;
		text-transform: uppercase;
		color: #6a7a8a;
		padding: 0 6px 4px;
	}

	.lb-row {
		display: flex;
		flex-direction: column;
		gap: 4px;
		padding: 7px 8px;
		border-radius: 10px;
		border: 1px solid transparent;
		background: rgba(18, 22, 28, 0.6);
		transition: border-color 0.15s;
	}
	.lb-row.self {
		border-color: #4a6a8a;
		background: rgba(20, 35, 55, 0.7);
	}
	.lb-row.opponent {
		border-color: #7a4a3a;
		background: rgba(40, 20, 15, 0.65);
	}
	.lb-row.dead {
		opacity: 0.38;
	}

	.lb-rank {
		font-size: 10px;
		color: #5a6a78;
		font-weight: 600;
	}

	.lb-info {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 4px;
	}

	.lb-name {
		font-size: 12px;
		font-weight: 600;
		color: #d5cec0;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		display: flex;
		align-items: center;
		gap: 4px;
		max-width: 110px;
	}

	.tag {
		font-size: 9px;
		font-weight: 700;
		padding: 1px 4px;
		border-radius: 4px;
		flex-shrink: 0;
	}
	.tag.you {
		background: #1e3a5a;
		color: #7ab8e8;
		border: 1px solid #3a6a9a;
	}
	.tag.vs {
		background: #4a1a10;
		color: #e87a5a;
		border: 1px solid #8a3a28;
	}
	.tag.bot {
		background: #1e2a1e;
		color: #6a9a6a;
		border: 1px solid #3a5a3a;
	}

	.lb-hp {
		font-size: 11px;
		font-weight: 700;
		color: #a8d8a8;
		flex-shrink: 0;
	}
	.lb-hp.low {
		color: #e88888;
	}
	.dead-label {
		font-size: 9px;
		color: #5a5a5a;
		font-style: italic;
	}

	.lb-board {
		display: flex;
		flex-wrap: wrap;
		gap: 3px;
		margin-top: 2px;
	}

	.lb-minion {
		display: flex;
		align-items: center;
		gap: 2px;
		padding: 2px 5px;
		border-radius: 5px;
		background: #1a1e24;
		border: 1px solid #2e3844;
		font-size: 10px;
		font-weight: 700;
	}
	.lb-minion.golden {
		border-color: #a07830;
		background: #231a08;
	}

	.lb-atk {
		color: #e8a860;
	}
	.lb-hp-mini {
		color: #80c880;
	}
</style>
