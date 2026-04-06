<script lang="ts">
	interface Props {
		name: string;
		health: number;
		tier: number;
		locked?: boolean;
		isSelf?: boolean;
	}

	let { name, health, tier, locked = false, isSelf = false }: Props = $props();
</script>

<div class="player-info" class:self={isSelf} class:locked>
	<span class="name">{name}{isSelf ? ' (you)' : ''}</span>
	<span class="hp" class:low={health <= 15}>♥ {health}</span>
	<span class="tier">T{tier}</span>
	{#if locked}
		<span class="lock-badge">✓ Ready</span>
	{/if}
</div>

<style>
	.player-info {
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 6px 12px;
		background: #12121c;
		border: 1px solid #2a2a3a;
		border-radius: 6px;
		font-size: 13px;
	}
	.player-info.self {
		border-color: #404060;
	}
	.player-info.locked {
		border-color: #406040;
	}
	.name {
		font-weight: 600;
		color: #ddd;
	}
	.hp {
		color: #60c060;
		font-weight: 700;
	}
	.hp.low {
		color: #e04040;
	}
	.tier {
		font-size: 11px;
		color: #888;
		background: #222;
		border-radius: 3px;
		padding: 1px 5px;
	}
	.lock-badge {
		font-size: 11px;
		color: #60c060;
	}
</style>
