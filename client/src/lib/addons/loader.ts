import { addonRegistry } from "./registry";
import type { ClientAddon } from "./types";

// addon id == path relative to lib/addons/ (e.g. "keywords/divine_shield")
export async function loadMatchAddons(ids: string[]): Promise<void> {
	const toLoad = ids.filter((id) => !addonRegistry.loadedIds().includes(id));
	await Promise.all(
		toLoad.map(async (id) => {
			try {
				const mod = await import(`./${id}.ts`);
				addonRegistry.register(mod.default as ClientAddon);
			} catch (e) {
				console.warn(`[addons] failed to load "${id}":`, e);
			}
		})
	);
}
