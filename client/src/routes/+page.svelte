<script lang="ts">
	import { onMount } from "svelte";
	import { combat } from "$lib/game/combat.svelte.js";
	import { connect, connection } from "$lib/game/connection.svelte.js";
	import { match } from "$lib/game/match.svelte.js";
	import { ui } from "$lib/game/ui.svelte.js";
	import Login from "$lib/views/Login.svelte";
	import Lobby from "$lib/views/Lobby.svelte";
	import HeroSelectView from "$lib/views/HeroSelectView.svelte";
	import GameView from "$lib/views/game/GameView.svelte";
	import GameOver from "$lib/views/GameOver.svelte";

	onMount(() => connect());

	function restart() {
		ui.screen = "login";
		ui.gameOverWinner = null;
		match.self = null;
		match.opponent = null;
		match.round = 0;
		match.phase = null;
		match.buySecondsLeft = null;
		combat.combatLog = [];
		combat.combatMeta = null;
		combat.combatResult = null;
		connection.matchId = null;
	}
</script>

{#if !connection.connected}
	<div class="overlay">Connecting…</div>
{/if}

{#if ui.error}
	<div class="toast">{ui.error}</div>
{/if}

{#if ui.screen === "login"}
	<Login />
{:else if ui.screen === "queued"}
	<Lobby />
{:else if ui.screen === "hero_select"}
	<HeroSelectView />
{:else if ui.screen === "game"}
	<GameView />
{:else if ui.screen === "game_over"}
	<GameOver onrestart={restart} />
{/if}

<style>
	:global(*, *::before, *::after) {
		box-sizing: border-box;
		margin: 0;
		padding: 0;
	}
	:global(body) {
		background: radial-gradient(circle at top, #23303b 0%, transparent 34%),
			linear-gradient(180deg, #10141a 0%, #090b0f 100%);
		color: #f2eadc;
		font-family: Georgia, "Times New Roman", serif;
		font-size: 14px;
		min-height: 100vh;
	}

	.overlay {
		position: fixed;
		inset: 0;
		background: #090b0fcc;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 16px;
		color: #c9c1b0;
		z-index: 99;
	}
	.toast {
		position: fixed;
		top: 18px;
		left: 50%;
		transform: translateX(-50%);
		background: #331717;
		border: 1px solid #8a4545;
		color: #ffd1d1;
		padding: 10px 18px;
		border-radius: 999px;
		font-size: 13px;
		z-index: 100;
		pointer-events: none;
	}
</style>
