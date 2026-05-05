<script lang="ts">
	import { addonRegistry } from "$lib/addons/registry";
	import { match } from "$lib/game/match.svelte.js";

	// Current state is the game phase; addons that introduce custom states
	// should publish their state name here via a shared store or prop.
	interface Props {
		state?: string;
	}
	let { state }: Props = $props();

	const currentState = $derived(state ?? match.phase ?? "");
	const overlays = $derived(addonRegistry.getActiveOverlays(currentState));
</script>

{#each overlays as overlay (overlay)}
	{@const Comp = overlay.component}
	<div class="overlay-layer" style:z-index={overlay.zIndex ?? 100}>
		<Comp {...overlay.props ?? {}} />
	</div>
{/each}

<style>
	.overlay-layer {
		position: fixed;
		inset: 0;
		pointer-events: none;
	}
</style>
