<script lang="ts">
	import type { CombatEvent, CombatResultMsg } from '../types.js';

	interface Props {
		events: CombatEvent[];
		result: CombatResultMsg | null;
		selfId: string;
	}

	let { events, result, selfId }: Props = $props();

	function describe(e: CombatEvent): string {
		switch (e.type) {
			case 'attack':
				return `${e.attacker_name} attacks ${e.defender_name}`;
			case 'damage_dealt': {
				const attackerHp = e.attacker_remaining_hp as number;
				const defenderHp = e.defender_remaining_hp as number;
				return `  → ${attackerHp >= 0 ? `attacker ${attackerHp}hp` : ''} / ${defenderHp >= 0 ? `defender ${defenderHp}hp` : ''}`;
			}
			case 'death':
				return `💀 ${e.minion_name} dies`;
			case 'buff':
				return `✨ ${e.target_name} +${e.attack}/+${e.health}`;
			case 'summon':
				return `➕ ${e.minion_name} summoned`;
			case 'damage':
				return `  ⚡ ${e.target_name} takes ${e.amount} (→ ${e.remaining_health}hp)`;
			default:
				return `[${e.type}]`;
		}
	}
</script>

<div class="combat-log">
	<div class="log-title">Combat log</div>
	<div class="log-scroll">
		{#each events as e}
			<div class="log-line" class:death={e.type === 'death'}>
				{describe(e)}
			</div>
		{/each}
		{#if events.length === 0}
			<div class="log-empty">Waiting for combat…</div>
		{/if}
	</div>
	{#if result}
		<div class="result" class:win={result.winner_player === selfId} class:loss={result.winner_player !== selfId && result.winner_player !== null}>
			{#if result.winner_player === null}
				Tie!
			{:else if result.winner_player === selfId}
				You won the round! Enemy takes {result.damage} damage.
			{:else}
				You lost the round. You take {result.damage} damage.
			{/if}
		</div>
	{/if}
</div>

<style>
	.combat-log {
		display: flex;
		flex-direction: column;
		gap: 6px;
	}
	.log-title {
		font-size: 11px;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: #888;
	}
	.log-scroll {
		background: #0c0c14;
		border: 1px solid #2a2a3a;
		border-radius: 6px;
		padding: 8px;
		font-size: 11px;
		font-family: monospace;
		color: #aaa;
		max-height: 180px;
		overflow-y: auto;
		display: flex;
		flex-direction: column;
		gap: 2px;
	}
	.log-line.death {
		color: #e06060;
	}
	.log-empty {
		color: #444;
		text-align: center;
		padding: 8px;
	}
	.result {
		padding: 8px 12px;
		border-radius: 6px;
		font-size: 13px;
		font-weight: 600;
		background: #1e1e2e;
		border: 1px solid #444;
		color: #ccc;
	}
	.result.win {
		border-color: #406040;
		color: #80d080;
	}
	.result.loss {
		border-color: #604040;
		color: #e06060;
	}
</style>
