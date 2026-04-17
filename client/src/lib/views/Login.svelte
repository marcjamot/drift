<script lang="ts">
	import { connection, send } from "$lib/game/connection.svelte.js";

	let nameInput = $state("");

	function login() {
		const n = nameInput.trim();
		if (n) send({ type: "login", name: n });
	}
</script>

<div class="splash">
	<h1 class="wordmark">drift</h1>
	<p class="tagline">a tavern game</p>

	{#if !connection.playerId}
		<form
			class="login-form"
			onsubmit={(e) => {
				e.preventDefault();
				login();
			}}
		>
			<input
				class="name-input"
				bind:value={nameInput}
				placeholder="your name"
				maxlength="20"
				disabled={!connection.connected}
			/>
			<button type="submit" class="btn primary" disabled={!connection.connected || !nameInput.trim()}>
				Continue
			</button>
		</form>
	{:else}
		<p class="greeting">Hi, <strong>{connection.playerName}</strong></p>
		<button class="btn primary lg" onclick={() => send({ type: "queue" })}>Find a match</button>
	{/if}
</div>

<style>
	.splash {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		height: 100vh;
		gap: 20px;
	}
	.wordmark {
		font-size: clamp(56px, 12vw, 90px);
		font-weight: 700;
		letter-spacing: -0.05em;
		color: #f4ecdf;
	}
	.tagline,
	.greeting {
		color: #b5a992;
	}
	.login-form {
		display: flex;
		flex-direction: column;
		gap: 10px;
		width: min(280px, 90vw);
	}
	.name-input {
		font-family: inherit;
		font-size: 16px;
		padding: 12px 16px;
		background: #171c22;
		border: 1px solid #3a444f;
		border-radius: 10px;
		color: #fff8ec;
		outline: none;
	}
	.name-input:focus {
		border-color: #8f7a57;
	}
	.btn {
		font-family: inherit;
		font-size: 13px;
		padding: 8px 14px;
		border-radius: 999px;
		border: 1px solid #4b5563;
		background: #1b2128;
		color: #f0e7d7;
		cursor: pointer;
		transition:
			background 0.15s,
			border-color 0.15s,
			color 0.15s,
			transform 0.15s;
		white-space: nowrap;
	}
	.btn:hover:not(:disabled) {
		background: #232b35;
		border-color: #8f7a57;
		transform: translateY(-1px);
	}
	.btn:disabled {
		opacity: 0.4;
		cursor: default;
	}
	.btn.primary {
		background: #6f5632;
		border-color: #b79258;
		color: #fff3da;
	}
	.btn.primary:hover:not(:disabled) {
		background: #81653c;
	}
	.btn.lg {
		font-size: 16px;
		padding: 12px 30px;
	}
</style>
