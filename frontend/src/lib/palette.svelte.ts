import { browser } from '$app/environment';
import { storageHealth } from './storageHealth.svelte';
import { APPLIED_PALETTE_KEY, appliedPalette, normalizePalette, PALETTE_KEY, type AppliedPalette, type Palette } from './palettes';
import { theme } from './theme.svelte';

/**
 * The reader's library palette (see $lib/palettes). Sets `data-palette` on
 * <html> to the palette the choice APPLIES — none for the house palette, and
 * for the Church year the season's — and re-colours the browser chrome to
 * match. Same shape as siteFont.svelte.ts; app.html's boot script applies the
 * stored value before first paint, so keep the two in step.
 */
class PalettePref {
	/** What the reader chose (and what syncs to their account). */
	current = $state<Palette>('parchment');
	#listening = false;

	/** What is painted: the choice, or the Church year's season today. */
	get applied(): AppliedPalette {
		return appliedPalette(this.current);
	}

	init() {
		if (!browser) return;
		try {
			this.current = normalizePalette(localStorage.getItem(PALETTE_KEY));
		} catch {
			/* storage blocked: stay on the house palette */
		}
		this.#apply();
		// The Church year turns with the calendar: a tab left open across a
		// season's first day takes the new colours when the reader comes back
		// (as the home hero's date and season dot do). Once per page.
		if (this.#listening) return;
		this.#listening = true;
		document.addEventListener('visibilitychange', () => {
			if (document.visibilityState === 'visible' && this.current === 'liturgical') this.#apply();
		});
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
		const applied = this.applied;
		const root = document.documentElement;
		if (applied === 'parchment') delete root.dataset.palette;
		else root.dataset.palette = applied;
		// The boot script can't compute the season (it has no calendar), so it
		// paints the one cached here; the app corrects it on load if it moved.
		try {
			if (this.current === 'liturgical') localStorage.setItem(APPLIED_PALETTE_KEY, applied);
			else localStorage.removeItem(APPLIED_PALETTE_KEY);
		} catch {
			/* the cache is a nicety: the app applies the right season anyway */
		}
		theme.refreshChrome();
	}
}

export const palette = new PalettePref();
