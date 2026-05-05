import type { ClientAddon, CardVisual, HeroVisual, EffectHandler, GameAction, GamePhase, GameScene, LayerDef } from "./types";

class AddonRegistry {
	private addons = new Map<string, ClientAddon>();
	private cards = new Map<string, CardVisual>();
	private heroes = new Map<string, HeroVisual>();
	private effects = new Map<string, EffectHandler[]>();
	private layers = new Map<GamePhase, LayerDef[]>();
	/** server addon id → client addon ids that listen to it */
	private listenerMap = new Map<string, string[]>();
	/** declared intent types → addon id that owns them */
	private intentOwners = new Map<string, string>();

	register(addon: ClientAddon): void {
		if (this.addons.has(addon.id)) return;
		this.addons.set(addon.id, addon);

		for (const [id, visual] of Object.entries(addon.cards ?? {})) this.cards.set(id, visual);
		for (const [id, visual] of Object.entries(addon.heroes ?? {})) this.heroes.set(id, visual);

		for (const [actionType, handler] of Object.entries(addon.effects ?? {})) {
			const list = this.effects.get(actionType) ?? [];
			list.push(handler);
			this.effects.set(actionType, list);
		}

		for (const [phase, layer] of Object.entries(addon.layers ?? {}) as [GamePhase, LayerDef][]) {
			const list = this.layers.get(phase) ?? [];
			list.push(layer);
			this.layers.set(phase, list);
		}

		for (const serverAddonId of addon.listens_to ?? []) {
			const listeners = this.listenerMap.get(serverAddonId) ?? [];
			listeners.push(addon.id);
			this.listenerMap.set(serverAddonId, listeners);
		}

		for (const intentType of addon.intents ?? []) {
			this.intentOwners.set(intentType, addon.id);
		}
	}

	unregister(addonId: string): void {
		const addon = this.addons.get(addonId);
		if (!addon) return;

		for (const id of Object.keys(addon.cards ?? {})) this.cards.delete(id);
		for (const id of Object.keys(addon.heroes ?? {})) this.heroes.delete(id);

		for (const [actionType, handler] of Object.entries(addon.effects ?? {})) {
			const list = this.effects.get(actionType) ?? [];
			this.effects.set(actionType, list.filter((h) => h !== handler));
		}

		for (const [phase, layer] of Object.entries(addon.layers ?? {}) as [GamePhase, LayerDef][]) {
			const list = this.layers.get(phase) ?? [];
			this.layers.set(phase, list.filter((l) => l !== layer));
		}

		for (const serverAddonId of addon.listens_to ?? []) {
			const listeners = this.listenerMap.get(serverAddonId) ?? [];
			this.listenerMap.set(serverAddonId, listeners.filter((id) => id !== addonId));
		}

		for (const intentType of addon.intents ?? []) {
			if (this.intentOwners.get(intentType) === addonId) {
				this.intentOwners.delete(intentType);
			}
		}

		this.addons.delete(addonId);
	}

	getCard(card_id: string): CardVisual | undefined {
		return this.cards.get(card_id);
	}

	getHero(card_id: string): HeroVisual | undefined {
		return this.heroes.get(card_id);
	}

	/** All layers for the given phase whose when() condition passes (or has no condition). */
	getActiveLayers(phase: GamePhase): LayerDef[] {
		return (this.layers.get(phase) ?? []).filter((l) => !l.when || l.when(phase));
	}

	/** Play all registered effects for the given action. */
	async playEffects(action: GameAction, scene: GameScene): Promise<void> {
		const handlers = this.effects.get(action.type) ?? [];
		await Promise.all(handlers.map((h) => h(action, scene)));
	}

	/** Client addon IDs listening to a given server addon. */
	getListeners(serverAddonId: string): string[] {
		return this.listenerMap.get(serverAddonId) ?? [];
	}

	/** Whether an intent type is declared by any loaded addon. */
	isKnownIntent(intentType: string): boolean {
		return this.intentOwners.has(intentType);
	}

	loadedIds(): string[] {
		return [...this.addons.keys()];
	}
}

export const addonRegistry = new AddonRegistry();
