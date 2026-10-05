import { browser } from '$app/environment';
import { storageHealth } from './storageHealth.svelte';
import { normalizePalette, PALETTE_KEY, type Palette } from './palettes';
import { theme } from './theme.svelte';

/**
 * The reader's library palette (see $lib/palettes). Sets `data-palette` on
 * <html> — none for the house palette — and re-colours the browser chrome to
 * match. Same shape as siteFont.svelte.ts; app.html's boot script applies the
 * stored value before first paint, so keep the two in step.
 */
class PalettePref {
	current = $state<Palette>('parchment');

	init() {
		if (!browser) return;
		try {
			this.current = normalizePalette(localStorage.getItem(PALETTE_KEY));
		} catch {
			/* storage blocked: stay on the house palette */
		}
		this.#apply();
	}

	set(v: Palette) {
		this.current = v;
		if (browser) {
			try {
				if (v === 'parchment') localStorage.removeItem(PALETTE_KEY);
				else localStorage.setItem(PALETTE_KEY, v);
			} catch {
				storageHealth.fail();
			}
		}
		this.#apply();
	}

	#apply() {
		if (!browser) return;
		const root = document.documentElement;
		if (this.current === 'parchment') delete root.dataset.palette;
		else root.dataset.palette = this.current;
		theme.refreshChrome();
	}
}

export const palette = new PalettePref();
