import { browser } from '$app/environment';
import { storageHealth } from './storageHealth.svelte';

/**
 * The site style — the interface's typeface, separate from the reader's:
 * `house` (Fraunces + Hanken), `classic` (EB Garamond headings) or
 * `hyperlegible` (Atkinson Hyperlegible Next throughout). This only sets
 * `data-site-font` on <html>; the CSS and why it lands on <body> are in
 * site-fonts.css. app.html's boot script applies the stored value before first
 * paint — keep the two in step. A bare string, like the theme, because that
 * script reads it with no parser.
 */
export type SiteFont = 'house' | 'classic' | 'hyperlegible';

export const SITE_FONTS: readonly SiteFont[] = ['house', 'classic', 'hyperlegible'];

const KEY = 'ochorus:site-font';

/** Normalise a stored value; anything unknown is the house style. */
export function normalizeSiteFont(v: string | null | undefined): SiteFont {
	return (SITE_FONTS as readonly string[]).includes(v ?? '') ? (v as SiteFont) : 'house';
}

class SiteFontPref {
	current = $state<SiteFont>('house');

	init() {
		if (!browser) return;
		try {
			this.current = normalizeSiteFont(localStorage.getItem(KEY));
		} catch {
			/* storage blocked: stay on the house style */
		}
		this.#apply();
	}

	set(v: SiteFont) {
		this.current = v;
		if (browser) {
			try {
				if (v === 'house') localStorage.removeItem(KEY);
				else localStorage.setItem(KEY, v);
			} catch {
				// Private mode / quota: the choice still applies for this visit, and
				// the banner says it will not survive — as for every other store.
				storageHealth.fail();
			}
		}
		this.#apply();
	}

	#apply() {
		if (!browser) return;
		const root = document.documentElement;
		if (this.current === 'house') delete root.dataset.siteFont;
		else root.dataset.siteFont = this.current;
	}
}

export const siteFont = new SiteFontPref();
