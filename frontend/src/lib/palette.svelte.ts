import { browser } from '$app/environment';
import { storageHealth } from './storageHealth.svelte';
import { canViewTransition, crossfade } from './crossfade';
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

/** The palette rules (static/palettes.css): linked only once a palette is
 *  applied, so the readers who keep the house palette never load them. */
export const PALETTE_SHEET = '/palettes.css';

let sheet: Promise<void> | null = null;

/** Link the palette sheet (once) and resolve when it has loaded, or failed:
 *  a palette without its sheet paints the house colours, which is the most a
 *  failure should cost. app.html's boot script may already have written it. */
export function loadPaletteSheet(): Promise<void> {
	if (sheet) return sheet;
	const have = document.head.querySelector<HTMLLinkElement>(`link[rel="stylesheet"][href="${PALETTE_SHEET}"]`);
	if (have?.sheet) return (sheet = Promise.resolve());
	const link = have ?? document.createElement('link');
	sheet = new Promise<void>((done) => {
		link.addEventListener('load', () => done(), { once: true });
		link.addEventListener('error', () => done(), { once: true });
		// A stalled request must not hold a reader's choice hostage.
		setTimeout(done, 2000);
	});
	if (!have) {
		link.rel = 'stylesheet';
		link.href = PALETTE_SHEET;
		document.head.append(link);
	}
	return sheet;
}

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
				// Wait for the palette rules before the crossfade captures the new
				// state, or it would fade to the house colours and then jump.
				// (Without a transition there is nothing to capture: apply now,
				// and the colours arrive with the sheet.)
				const swap = () => crossfade(() => this.#apply());
				if (this.applied === 'parchment' || !canViewTransition()) swap();
				else void loadPaletteSheet().then(swap);
				return;
			}
		}
		this.#apply();
	}

	#apply() {
		if (!browser) return;
		const applied = this.applied;
		const root = document.documentElement;
		// Already linked by the boot script on a palette page, or by set();
		// this covers the Church year turning to a new season in an open tab.
		if (applied !== 'parchment') void loadPaletteSheet();
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
