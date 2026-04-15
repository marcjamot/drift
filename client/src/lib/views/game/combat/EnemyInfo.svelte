<script lang="ts">
	interface Props {
		name: string;
		health: number;
	}
	let { name, health }: Props = $props();
</script>

<div class="arena-nameplate opp-plate">
	<span class="arena-kicker">Enemy</span>
	<span class="arena-name">{name}</span>
	<span class="arena-hp" class:low={health <= 15}>♥ {health}</span>
</div>

<style>
	.arena-nameplate {
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 10px 20px;
	}
	.opp-plate {
		border-bottom: 1px solid #2a2218;
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
</style>
