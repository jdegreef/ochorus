import { browser } from '$app/environment';
import { storageHealth } from './storageHealth.svelte';
import { crossfade } from './crossfade';
import {
	APPLIED_PALETTE_KEY,
	appliedPalette,
	normalizeApplied,
	normalizePalette,
	PALETTE_KEY,
	type AppliedPalette,
	type Palette
} from './palettes';
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
		// A choice that follows the calendar (the Church year) takes a new
		// season's colours when the reader comes back to a tab left open across
		// its first day, as the home hero's date and season dot do. Repaints
		// only when what should be applied has moved. Once per page.
		if (this.#listening) return;
		this.#listening = true;
		document.addEventListener('visibilitychange', () => {
			if (document.visibilityState !== 'visible') return;
			if (this.applied !== normalizeApplied(document.documentElement.dataset.palette)) this.#apply();
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
			if (this.applied !== normalizeApplied(document.documentElement.dataset.palette)) {
				crossfade(() => this.#apply());
				return;
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
		// The boot script can't resolve a choice (it has no calendar), so when
		// what is painted differs from what was chosen it paints the palette
		// cached here; the app corrects it on load if the season moved.
		try {
			if (applied !== this.current) localStorage.setItem(APPLIED_PALETTE_KEY, applied);
			else localStorage.removeItem(APPLIED_PALETTE_KEY);
		} catch {
			/* the cache is a nicety: the app applies the right season anyway */
		}
		theme.refreshChrome();
	}
}

export const palette = new PalettePref();
