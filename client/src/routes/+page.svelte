<script lang="ts">
	import { onMount, untrack } from 'svelte';
	import { gs, connect, send } from '$lib/gameStore.svelte.js';
	import type { CombatEvent, MinionSnapshot } from '$lib/types.js';
	import Board from '$lib/components/Board.svelte';
	import Shop from '$lib/components/Shop.svelte';

	onMount(() => connect());

	let nameInput = $state('');
	let selectedBoardIdx = $state<number | null>(null);
	let selectedHandIdx = $state<number | null>(null);
	let concedeArmed = $state(false);
	let concedeTimer = 0;
	let newBoardIds = $state(new Set<string>());
	let prevBoardIds = new Set<string>();
	let healthFlash = $state(false);
	let prevHealth = -1;

	type AnimPhase = 'idle' | 'animating' | 'done';

	let animPhase = $state<AnimPhase>('idle');
	let animSelfBoard = $state<MinionSnapshot[]>([]);
	let animOppBoard = $state<MinionSnapshot[]>([]);
	let animHighlights = $state(new Set<string>());
	let animAttackers = $state(new Set<string>());
	let animTargets = $state(new Set<string>());
	let animStricken = $state(new Set<string>());
	let animDying = $state(new Set<string>());
	let animNewIds = $state(new Set<string>());
	let animText = $state('');
	let animStarted = false;

	function login() {
		const n = nameInput.trim();
		if (n) send({ type: 'login', name: n });
	}

	function toggleBoardSelect(i: number) {
		selectedHandIdx = null;
		selectedBoardIdx = selectedBoardIdx === i ? null : i;
	}

	function toggleHandSelect(i: number) {
		selectedBoardIdx = null;
		selectedHandIdx = selectedHandIdx === i ? null : i;
	}

	function sellSelected() {
		if (selectedBoardIdx === null) return;
		send({ type: 'sell', board_index: selectedBoardIdx });
		selectedBoardIdx = null;
	}

	function playSelected() {
		if (selectedHandIdx === null) return;
		send({ type: 'play', hand_index: selectedHandIdx });
		selectedHandIdx = null;
	}

	function shiftSelected(dir: -1 | 1) {
		if (selectedBoardIdx === null || !gs.self) return;
		const to = selectedBoardIdx + dir;
		if (to < 0 || to >= gs.self.board.length) return;
		send({ type: 'reorder', from_index: selectedBoardIdx, to_index: to });
		selectedBoardIdx = to;
	}

	function lock() {
		send({ type: 'lock' });
		selectedBoardIdx = null;
		selectedHandIdx = null;
	}

	function concede() {
		if (!concedeArmed) {
			concedeArmed = true;
			clearTimeout(concedeTimer);
			concedeTimer = setTimeout(() => (concedeArmed = false), 3000) as unknown as number;
		} else {
			clearTimeout(concedeTimer);
			concedeArmed = false;
			send({ type: 'concede' });
		}
	}

	$effect(() => {
		if (!gs.self) return;
		const ids = gs.self.board.map((m) => m.instance_id);
		const added = ids.filter((id) => !prevBoardIds.has(id));
		prevBoardIds = new Set(ids);
		if (added.length === 0) return;
		newBoardIds = new Set(added);
		setTimeout(() => (newBoardIds = new Set()), 500);
	});

	$effect(() => {
		if (!gs.self) return;
		if (selectedBoardIdx !== null && selectedBoardIdx >= gs.self.board.length) selectedBoardIdx = null;
		if (selectedHandIdx !== null && selectedHandIdx >= gs.self.hand.length) selectedHandIdx = null;
	});

	$effect(() => {
		if (!gs.self) return;
		const h = gs.self.health;
		if (prevHealth !== -1 && h < prevHealth) {
			healthFlash = true;
			setTimeout(() => (healthFlash = false), 900);
		}
		prevHealth = h;
	});

	$effect(() => {
		const log = gs.combatLog;
		const meta = gs.combatMeta;

		if (!meta || !gs.playerId) return;
		if (animStarted) return;

		animStarted = true;
		const isSelfA = meta.players[0] === gs.playerId;
		untrack(() => {
			animSelfBoard = isSelfA ? [...meta.initial_a] : [...meta.initial_b];
			animOppBoard = isSelfA ? [...meta.initial_b] : [...meta.initial_a];
			animPhase = 'animating';
		});
		runCombatAnim(log, isSelfA);
	});

	$effect(() => {
		if (gs.phase !== 'buy' || animPhase !== 'done') return;
		animStarted = false;
		animPhase = 'idle';
		animText = '';
		animHighlights = new Set();
		animAttackers = new Set();
		animTargets = new Set();
		animStricken = new Set();
		animDying = new Set();
		animNewIds = new Set();
		gs.combatLog = [];
		gs.combatMeta = null;
		gs.combatResult = null;
	});

	function sleep(ms: number) {
		return new Promise<void>((r) => setTimeout(r, ms));
	}

	function updateMinionHealth(id: string, hp: number) {
		animSelfBoard = animSelfBoard.map((m) => (m.instance_id === id ? { ...m, health: hp } : m));
		animOppBoard = animOppBoard.map((m) => (m.instance_id === id ? { ...m, health: hp } : m));
	}

	function updateMinionBuff(id: string, atk: number, hp: number) {
		animSelfBoard = animSelfBoard.map((m) =>
			m.instance_id === id ? { ...m, attack: m.attack + atk, health: m.health + hp } : m
		);
		animOppBoard = animOppBoard.map((m) =>
			m.instance_id === id ? { ...m, attack: m.attack + atk, health: m.health + hp } : m
		);
	}

	async function runCombatAnim(events: CombatEvent[], isSelfA: boolean) {
		for (const e of events) {
			if (e.type === 'attack') {
				const aid = e.attacker_id as string;
				const did = e.defender_id as string;
				animAttackers = new Set([aid]);
				animTargets = new Set();
				animHighlights = new Set([aid]);
				animText = `${e.attacker_name} prepares`;
				await sleep(800);
				animTargets = new Set([did]);
				animHighlights = new Set([aid]);
				animText = `${e.attacker_name} targets ${e.defender_name}`;
				await sleep(850);
			} else if (e.type === 'damage_dealt') {
				const shaken = new Set<string>();
				if ((e.damage_to_attacker as number) > 0) shaken.add(e.attacker_id as string);
				if ((e.damage_to_defender as number) > 0) shaken.add(e.defender_id as string);
				animStricken = shaken;
				animText = 'Impact';
				updateMinionHealth(e.attacker_id as string, e.attacker_remaining_hp as number);
				updateMinionHealth(e.defender_id as string, e.defender_remaining_hp as number);
				await sleep(1020);
				animAttackers = new Set();
				animTargets = new Set();
				animStricken = new Set();
				animHighlights = new Set();
			} else if (e.type === 'death') {
				const mid = e.minion_id as string;
				animDying = new Set([...animDying, mid]);
				animText = `${e.minion_name} dies`;
				await sleep(550);
				animSelfBoard = animSelfBoard.filter((m) => m.instance_id !== mid);
				animOppBoard = animOppBoard.filter((m) => m.instance_id !== mid);
				animDying = new Set([...animDying].filter((id) => id !== mid));
			} else if (e.type === 'buff') {
				const tid = e.target_id as string;
				animHighlights = new Set([tid]);
				animText = `${e.target_name} grows stronger`;
				updateMinionBuff(tid, e.attack as number, e.health as number);
				await sleep(500);
				animHighlights = new Set();
			} else if (e.type === 'summon') {
				const m = e.minion as MinionSnapshot;
				if (m) {
					const side = e.side as number;
					const isOppSide = isSelfA ? side === 1 : side === 0;
					animNewIds = new Set([m.instance_id]);
					if (isOppSide) animOppBoard = [...animOppBoard, m];
					else animSelfBoard = [...animSelfBoard, m];
					animText = `${m.name} summoned`;
					animHighlights = new Set([m.instance_id]);
					await sleep(400);
					animHighlights = new Set();
					setTimeout(() => (animNewIds = new Set()), 500);
				}
			} else if (e.type === 'damage') {
				updateMinionHealth(e.target_id as string, e.remaining_health as number);
				await sleep(180);
			}
		}

		animHighlights = new Set();
		animAttackers = new Set();
		animTargets = new Set();
		animStricken = new Set();
		animDying = new Set();
		const result = gs.combatResult;
		if (result) {
			if (result.winner_player === null) animText = 'Tie!';
			else if (result.winner_player === gs.playerId) animText = 'You won this round';
			else animText = 'You lost this round';
		} else {
			animText = '';
		}
		animPhase = 'done';
		await sleep(events.length > 0 ? 900 : 1400);
	}

	const combatVisible = $derived(
		gs.phase === 'combat' || animPhase !== 'idle' || gs.combatMeta !== null
	);
	const showingSelf = $derived(combatVisible ? animSelfBoard : (gs.self?.board ?? []));
	const showingOpp = $derived(combatVisible ? animOppBoard : (gs.opponent?.board ?? []));

	function restart() {
		gs.screen = 'login';
		gs.gameOverWinner = null;
		gs.self = null;
		gs.opponent = null;
		selectedBoardIdx = null;
		selectedHandIdx = null;
	}
</script>

{#if !gs.connected}
	<div class="overlay">Connecting…</div>
{/if}

{#if gs.error}
	<div class="toast">{gs.error}</div>
{/if}

{#if gs.screen === 'login'}
	<div class="splash">
		<h1 class="wordmark">drift</h1>
		<p class="tagline">a tavern game</p>

		{#if !gs.playerId}
			<form class="login-form" onsubmit={(e) => { e.preventDefault(); login(); }}>
				<input
					class="name-input"
					bind:value={nameInput}
					placeholder="your name"
					maxlength="20"
					disabled={!gs.connected}
				/>
				<button type="submit" class="btn primary" disabled={!gs.connected || !nameInput.trim()}>
					Continue
				</button>
			</form>
		{:else}
			<p class="greeting">Hi, <strong>{gs.playerName}</strong></p>
			<button class="btn primary lg" onclick={() => send({ type: 'queue' })}>Find a match</button>
		{/if}
	</div>
{:else if gs.screen === 'queued'}
	<div class="splash">
		<h1 class="wordmark">drift</h1>
		<p class="waiting">Looking for an opponent</p>
		<div class="dots"><span></span><span></span><span></span></div>
	</div>
{:else if gs.screen === 'game' && gs.self && gs.opponent}
	<div class="game-shell" class:combat-mode={gs.phase === 'combat'} class:buy-mode={gs.phase === 'buy'}>
		<header class="topbar">
			<div class="identity">
				<div class="nameplate">{gs.self.name}</div>
				<div class="round-chip">Round {gs.round}</div>
				<div class="health-chip" class:low={gs.self.health <= 15}>♥ {gs.self.health}</div>
				<div class="health-chip enemy" class:low={gs.opponent.health <= 15}>
					{gs.opponent.name} · ♥ {gs.opponent.health}
				</div>
			</div>

			{#if !combatVisible && gs.phase === 'buy'}
				<div class="controls">
					<span class="turn-timer" class:urgent={(gs.buySecondsLeft ?? 99) <= 5}>
						{gs.buySecondsLeft ?? 0}s
					</span>
					<button class="btn concede" onclick={concede}>
						{concedeArmed ? 'Confirm?' : 'Concede'}
					</button>
					<button class="btn end-turn" onclick={lock} disabled={gs.self.locked}>
						{gs.self.locked ? '✓ Waiting…' : 'End Turn'}
					</button>
				</div>
			{:else}
				<div class="combat-status">
					<span class="phase-chip">Combat</span>
					{#if animText}
						<span class="anim-text">{animText}</span>
					{/if}
				</div>
			{/if}
		</header>

		{#if !combatVisible && gs.phase === 'buy'}
			<div class="buy-layout" class:flash={healthFlash}>
				<section class="panel shop-panel">
					<Shop self={gs.self} />
				</section>

				<section class="panel board-panel">
					<div class="section-head">
						<div>
							<div class="section-kicker">Board</div>
							<div class="section-title">Current warband</div>
						</div>
						<div class="meta-row">
							<span class="meta-pill">Tier {gs.self.tavern_tier}</span>
							<span class="meta-pill gold">⬡ {gs.self.gold}/{gs.self.max_gold}</span>
						</div>
					</div>
					<Board
						minions={gs.self.board}
						size="medium"
						align="center"
						emptyLabel="Play minions from your hand"
						selectable={true}
						selectedIndex={selectedBoardIdx}
						newIds={newBoardIds}
						onselect={toggleBoardSelect}
					/>
					{#if selectedBoardIdx !== null}
						<div class="action-row">
							<button class="btn sm" onclick={() => shiftSelected(-1)}>← Move</button>
							<button class="btn sm danger" onclick={sellSelected}>Sell (1g)</button>
							<button class="btn sm" onclick={() => shiftSelected(1)}>Move →</button>
							<button class="btn sm ghost" onclick={() => (selectedBoardIdx = null)}>Clear</button>
						</div>
					{/if}
				</section>

				<section class="panel hand-panel">
					<div class="section-head">
						<div>
							<div class="section-kicker">Hand</div>
							<div class="section-title">Bought cards wait here</div>
						</div>
						<span class="meta-pill">Cards {gs.self.hand.length}</span>
					</div>
					<Board
						minions={gs.self.hand}
						size="small"
						align="center"
						emptyLabel="Buy from the shop to build your hand"
						selectable={true}
						selectedIndex={selectedHandIdx}
						onselect={toggleHandSelect}
					/>
					{#if selectedHandIdx !== null}
						<div class="action-row">
							<button class="btn primary" onclick={playSelected} disabled={gs.self.board.length >= 7}>
								Play To Board
							</button>
							<button class="btn sm ghost" onclick={() => (selectedHandIdx = null)}>Clear</button>
						</div>
					{/if}
				</section>
			</div>
		{:else}
			<div class="combat-layout">
				<section class="combat-side enemy-side">
					<div class="section-head centered">
						<div class="section-kicker">Enemy Board</div>
						<div class="section-title">{gs.opponent.name}</div>
					</div>
					<Board
						minions={showingOpp}
						size="large"
						align="center"
						emptyLabel="No survivors"
						highlightIds={animHighlights}
						attackingIds={animAttackers}
						targetedIds={animTargets}
						strickenIds={animStricken}
						attackDirection="down"
						showHealthLeft={true}
						dyingIds={animDying}
						newIds={animPhase !== 'idle' ? animNewIds : new Set()}
					/>
				</section>

				<section class="combat-center">
					{#if gs.combatResult}
						<div
							class="result-banner"
							class:win={gs.combatResult.winner_player === gs.self.player_id}
							class:loss={gs.combatResult.winner_player !== null &&
								gs.combatResult.winner_player !== gs.self.player_id}
						>
							{#if gs.combatResult.winner_player === null}
								Tie, no damage dealt
							{:else if gs.combatResult.winner_player === gs.self.player_id}
								You won, opponent takes {gs.combatResult.damage}
							{:else}
								You lost, you take {gs.combatResult.damage}
							{/if}
						</div>
					{:else}
						<div class="combat-banner">{animText || 'Combat unfolding'}</div>
					{/if}
				</section>

				<section class="combat-side player-side" class:flash={healthFlash}>
					<div class="section-head centered">
						<div class="section-kicker">Your Board</div>
						<div class="section-title">{gs.self.name}</div>
					</div>
					<Board
						minions={showingSelf}
						size="large"
						align="center"
						emptyLabel="No survivors"
						highlightIds={animHighlights}
						attackingIds={animAttackers}
						targetedIds={animTargets}
						strickenIds={animStricken}
						attackDirection="up"
						showHealthLeft={true}
						dyingIds={animDying}
						newIds={animPhase !== 'idle' ? animNewIds : new Set()}
					/>
				</section>
			</div>
		{/if}
	</div>
{:else if gs.screen === 'game_over'}
	<div class="game-over">
		<div class="go-content">
			{#if gs.gameOverWinner === gs.playerId}
				<div class="go-result win">Victory</div>
				<div class="go-sub">Well played, {gs.playerName}.</div>
			{:else if gs.gameOverWinner}
				<div class="go-result loss">Defeat</div>
				<div class="go-sub">Better luck next time.</div>
			{:else}
				<div class="go-result">Game over</div>
			{/if}
			<button class="btn primary lg" onclick={restart}>Play again</button>
		</div>
	</div>
{/if}

<style>
	:global(*, *::before, *::after) { box-sizing: border-box; margin: 0; padding: 0; }
	:global(body) {
		background:
			radial-gradient(circle at top, #23303b 0%, transparent 34%),
			linear-gradient(180deg, #10141a 0%, #090b0f 100%);
		color: #f2eadc;
		font-family: Georgia, 'Times New Roman', serif;
		font-size: 14px;
		min-height: 100vh;
	}

	.overlay {
		position: fixed; inset: 0;
		background: #090b0fcc;
		display: flex; align-items: center; justify-content: center;
		font-size: 16px; color: #c9c1b0; z-index: 99;
	}
	.toast {
		position: fixed; top: 18px; left: 50%; transform: translateX(-50%);
		background: #331717; border: 1px solid #8a4545;
		color: #ffd1d1; padding: 10px 18px; border-radius: 999px;
		font-size: 13px; z-index: 100; pointer-events: none;
	}

	.splash {
		display: flex; flex-direction: column;
		align-items: center; justify-content: center;
		height: 100vh; gap: 20px;
	}
	.wordmark {
		font-size: clamp(56px, 12vw, 90px);
		font-weight: 700;
		letter-spacing: -0.05em;
		color: #f4ecdf;
	}
	.tagline, .greeting, .waiting { color: #b5a992; }
	.login-form { display: flex; flex-direction: column; gap: 10px; width: min(280px, 90vw); }
	.name-input {
		font-family: inherit; font-size: 16px;
		padding: 12px 16px;
		background: #171c22; border: 1px solid #3a444f;
		border-radius: 10px; color: #fff8ec; outline: none;
	}
	.name-input:focus { border-color: #8f7a57; }
	.dots { display: flex; gap: 6px; }
	.dots span {
		width: 7px; height: 7px; border-radius: 50%;
		background: #6b624f;
		animation: pulse 1.2s ease-in-out infinite;
	}
	.dots span:nth-child(2) { animation-delay: 0.2s; }
	.dots span:nth-child(3) { animation-delay: 0.4s; }
	@keyframes pulse { 0%, 80%, 100% { opacity: 0.35; } 40% { opacity: 1; } }

	.btn {
		font-family: inherit; font-size: 13px;
		padding: 8px 14px; border-radius: 999px;
		border: 1px solid #4b5563; background: #1b2128;
		color: #f0e7d7; cursor: pointer;
		transition: background 0.15s, border-color 0.15s, color 0.15s, transform 0.15s;
		white-space: nowrap;
	}
	.btn:hover:not(:disabled) {
		background: #232b35;
		border-color: #8f7a57;
		transform: translateY(-1px);
	}
	.btn:disabled { opacity: 0.4; cursor: default; }
	.btn.primary { background: #6f5632; border-color: #b79258; color: #fff3da; }
	.btn.primary:hover:not(:disabled) { background: #81653c; }
	.btn.lg { font-size: 16px; padding: 12px 30px; }
	.btn.sm { font-size: 12px; padding: 6px 12px; }
	.btn.danger { border-color: #8a4545; color: #ffd1d1; }
	.btn.ghost { background: transparent; border-color: #3a444f; color: #b5a992; }
	.btn.end-turn { background: #26462f; border-color: #5f9d69; color: #e0ffdd; min-width: 140px; }
	.btn.concede { background: transparent; border-color: transparent; color: #b58f8f; }

	.game-shell {
		display: flex;
		flex-direction: column;
		height: 100vh;
		padding: 18px;
		gap: 18px;
		overflow: hidden;
	}
	.game-shell.combat-mode {
		background:
			radial-gradient(circle at center, #2b2320 0%, transparent 32%),
			linear-gradient(180deg, #140f0d 0%, #090b0f 100%);
	}
	.topbar {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 16px;
		padding: 14px 18px;
		border-radius: 22px;
		background: rgba(12, 15, 19, 0.78);
		border: 1px solid #2f3944;
		backdrop-filter: blur(10px);
	}
	.identity, .controls, .combat-status {
		display: flex;
		align-items: center;
		gap: 10px;
		flex-wrap: wrap;
	}
	.nameplate, .round-chip, .health-chip, .phase-chip, .meta-pill {
		padding: 6px 12px;
		border-radius: 999px;
		border: 1px solid #37424d;
		background: #171c22;
	}
	.nameplate {
		font-size: 18px;
		font-weight: 700;
		color: #fff4df;
	}
	.health-chip.low { color: #ffb0b0; border-color: #8a4545; }
	.health-chip.enemy { color: #d9ccbb; }
	.turn-timer {
		min-width: 58px;
		text-align: center;
		padding: 8px 12px;
		border-radius: 999px;
		border: 1px solid #6a7d92;
		background: #1d2833;
		color: #e8f0fa;
		font-size: 13px;
		font-weight: 700;
	}
	.turn-timer.urgent {
		border-color: #c77474;
		background: #3a1e1e;
		color: #ffd6d6;
	}
	.anim-text {
		font-size: 14px;
		color: #f0d9ae;
		animation: fade-in 0.25s ease-out;
	}
	@keyframes fade-in { from { opacity: 0; } to { opacity: 1; } }

	.buy-layout {
		display: grid;
		grid-template-rows: auto minmax(200px, 1fr) minmax(160px, auto);
		gap: 18px;
		min-height: 0;
		flex: 1;
		overflow: auto;
		padding-right: 4px;
	}
	.buy-layout.flash, .player-side.flash {
		animation: dmg-flash 0.8s ease-out;
	}
	@keyframes dmg-flash {
		0%   { filter: brightness(1.18) saturate(1.2); }
		100% { filter: none; }
	}

	.panel, .combat-side, .combat-center {
		border-radius: 24px;
		background: rgba(12, 15, 19, 0.82);
		border: 1px solid #2f3944;
		backdrop-filter: blur(8px);
	}
	.panel {
		padding: 20px;
		display: flex;
		flex-direction: column;
		gap: 16px;
		min-height: 0;
	}
	.shop-panel { align-items: center; }
	.board-panel { min-height: 220px; }
	.hand-panel { min-height: 160px; }
	.section-head {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 12px;
		flex-wrap: wrap;
	}
	.section-head.centered {
		justify-content: center;
		text-align: center;
	}
	.section-kicker {
		font-size: 11px;
		letter-spacing: 0.14em;
		text-transform: uppercase;
		color: #b5a992;
	}
	.section-title {
		font-size: 28px;
		line-height: 1;
		color: #fff4df;
	}
	.meta-row, .action-row {
		display: flex;
		align-items: center;
		gap: 10px;
		flex-wrap: wrap;
	}
	.meta-pill.gold { color: #ffd87a; border-color: #7f6330; }
	.action-row { justify-content: center; }

	.combat-layout {
		display: grid;
		grid-template-rows: 1fr auto 1fr;
		gap: 18px;
		flex: 1;
		min-height: 0;
	}
	.combat-side {
		padding: 22px;
		display: flex;
		flex-direction: column;
		gap: 18px;
		min-height: 0;
	}
	.enemy-side {
		animation: stage-in 0.45s ease-out;
	}
	.player-side {
		animation: stage-in 0.45s 0.08s ease-out both;
	}
	.combat-center {
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 12px;
		min-height: 92px;
	}
	.combat-banner, .result-banner {
		padding: 14px 22px;
		border-radius: 999px;
		font-size: 18px;
		text-align: center;
		background: #1a1410;
		border: 1px solid #5a4833;
		color: #f4dfbb;
	}
	.result-banner.win {
		background: #132116;
		border-color: #4b8052;
		color: #d8ffdc;
	}
	.result-banner.loss {
		background: #2a1313;
		border-color: #924c4c;
		color: #ffd6d6;
	}
	@keyframes stage-in {
		from { opacity: 0; transform: translateY(14px); }
		to { opacity: 1; transform: translateY(0); }
	}

	.game-over {
		height: 100vh;
		display: flex; align-items: center; justify-content: center;
		animation: go-reveal 0.6s ease-out;
	}
	@keyframes go-reveal {
		from { opacity: 0; }
		to   { opacity: 1; }
	}
	.go-content {
		display: flex; flex-direction: column;
		align-items: center; gap: 18px;
	}
	.go-result {
		font-size: 64px; font-weight: 700;
		letter-spacing: -0.03em;
		color: #f2eadc;
	}
	.go-result.win { color: #91d694; }
	.go-result.loss { color: #df8f8f; }
	.go-sub { font-size: 15px; color: #b5a992; }

	@media (max-width: 900px) {
		.game-shell {
			padding: 12px;
			gap: 12px;
		}
		.topbar {
			padding: 12px;
		}
		.section-title {
			font-size: 22px;
		}
		.buy-layout, .combat-layout {
			gap: 12px;
		}
		.panel, .combat-side {
			padding: 14px;
		}
		.combat-banner, .result-banner {
			font-size: 15px;
			padding: 12px 16px;
		}
	}
</style>
