import type { Component } from "svelte";

// ---------------------------------------------------------------------------
// Shared visual primitives
// ---------------------------------------------------------------------------

export interface AnimationDef {
	type: "css" | "lottie" | "spritesheet";
	src: string;
	duration_ms?: number;
	loop?: boolean;
}

export interface CardVisual {
	card_id: string;
	art: string;
	frame?: string;
	tribe?: string;
	tribe_icon?: string;
	animations?: {
		idle?: AnimationDef;
		attack?: AnimationDef;
		death?: AnimationDef;
		spawn?: AnimationDef;
	};
}

export interface HeroVisual {
	card_id: string;
	portrait: string;
	power_icon?: string;
	animations?: {
		idle?: AnimationDef;
		power_activate?: AnimationDef;
	};
}

// ---------------------------------------------------------------------------
// Scene — interface for effects to interact with the rendered game
// ---------------------------------------------------------------------------

export interface GameScene {
	getMinionEl(instance_id: string): HTMLElement | null;
	getPlayerEl(player_id: string): HTMLElement | null;
	spawnEffect(el: HTMLElement, effect: AnimationDef): Promise<void>;
	playSound(src: string): void;
}

// ---------------------------------------------------------------------------
// Action — a single entry from the replay log
// ---------------------------------------------------------------------------

export interface GameAction {
	seq: number;
	at: number;
	type: string;
	data: Record<string, unknown>;
	store: Record<string, unknown>;
	visible_to?: string[];
}

// ---------------------------------------------------------------------------
// Layers — Svelte components mounted during a game phase
// ---------------------------------------------------------------------------

export type GamePhase = "begin" | "hero_select" | "shop" | "combat" | "end" | "game_over";

/**
 * TIntent is the union of intent types this layer is allowed to send.
 * Typed via the parent addon's intents declaration.
 */
export interface LayerDef<TIntent = never> {
	/**
	 * Svelte component to render. Receives `{ scene, send }` as props.
	 * `send` is typed to only accept the intents declared on the addon.
	 */
	component: Component<{ scene: GameScene; send: (intent: TIntent) => void }>;
	/** Optional predicate — layer only mounts when this returns true. */
	when?: (phase: GamePhase) => boolean;
}

// ---------------------------------------------------------------------------
// Effects — visual reactions to named action types from the server
// ---------------------------------------------------------------------------

export type EffectHandler = (action: GameAction, scene: GameScene) => void | Promise<void>;

// ---------------------------------------------------------------------------
// ClientAddon — the shape every client addon exports as default
//
// TIntent: union of intent object types this addon can send to the server.
//          Set to `never` for view-only addons with no interactions.
//
// Addon IDs are unique per side. Use `listens_to` to declare which server
// addon IDs this client addon depends on. The engine uses this for
// dependency validation and to route actions from those server addons.
// ---------------------------------------------------------------------------

export interface ClientAddon<TIntent = never> {
	/** Unique client-side addon identifier. */
	id: string;
	/**
	 * Server addon IDs this client addon listens to.
	 * Actions emitted by those server addons will be routed to this addon's
	 * effect handlers. Multiple client addons may listen to the same server addon.
	 */
	listens_to?: string[];
	/**
	 * Declared intent type strings this addon may send to the server.
	 * The engine validates inbound messages against this list — unknown types
	 * are dropped before reaching any handler.
	 */
	intents?: string[];
	/** Card visuals keyed by card_id. */
	cards?: Record<string, CardVisual>;
	/** Hero visuals keyed by card_id. */
	heroes?: Record<string, HeroVisual>;
	/** Svelte layers mounted during matching phases. */
	layers?: Partial<Record<GamePhase, LayerDef<TIntent>>>;
	/** Visual handlers keyed by action type from the replay log. */
	effects?: Record<string, EffectHandler>;
}
