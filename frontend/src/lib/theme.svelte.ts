import { browser } from '$app/environment';
import { normalizePalette, PALETTE_COLORS } from './palettes';
import type { IconName } from './components/Icon.svelte';

/**
 * Theme preference and the concrete theme it resolves to.
 *
 * `preference` is what the reader chose and what we persist: `system` follows
 * the OS (`prefers-color-scheme`, live), while `light` / `dark` / `sepia` pin a
 * fixed look. `current` is the resolved theme actually written to
 * `data-theme` — always one of light / dark / sepia. The boot script in
 * app.html applies the same resolution before hydration to avoid a flash; keep
 * the two in step.
 */

// hex-ok-file: these are the literal values shipped in <meta name="theme-color">,
// which paints the browser's own chrome. A var() is not resolvable there — the
// value has to be a real colour, and it has to equal each theme's --bg.
export type ThemePref = 'system' | 'light' | 'dark' | 'sepia';
export type ThemeApplied = 'light' | 'dark' | 'sepia';

const PREFS: readonly ThemePref[] = ['system', 'light', 'dark', 'sepia'];

/** Every theme choice with its label key and icon, in display order
 *  (lightest to darkest after System) — Settings, the header's quick
 *  settings, the More sheet and the reader's Aa panel all list from this. */
export const THEME_OPTIONS: readonly { v: ThemePref; k: string; icon: IconName }[] = [
	{ v: 'system', k: 'settings.themeSystem', icon: 'contrast' },
	{ v: 'light', k: 'settings.themeLight', icon: 'sun' },
	{ v: 'sepia', k: 'settings.themeSepia', icon: 'page' },
	{ v: 'dark', k: 'settings.themeDark', icon: 'moon' }
];

// Browser-UI colour (address bar / status bar) per applied theme; must match
// the `--bg` of each theme in app.css and the map in the app.html boot script.
const THEME_COLOR: Record<ThemeApplied, string> = {
	light: '#faf6ef',
	dark: '#16130f',
	sepia: '#f4ecd8'
};

/** Normalise a stored/synced value to a valid preference. 'paper' is the
 *  legacy name for the light theme (old profiles/localStorage may hold it). */
export function normalizePref(v: string | null | undefined): ThemePref {
	if (v === 'paper') return 'light';
	return (PREFS as readonly string[]).includes(v ?? '') ? (v as ThemePref) : 'system';
}

class Theme {
	/** The reader's stored choice; 'system' tracks the OS. */
	preference = $state<ThemePref>('system');
	/** The resolved theme currently applied (what `data-theme` is set to). */
	current = $state<ThemeApplied>('light');
	#mql: MediaQueryList | null = null;

	init() {
		if (!browser) return;
		this.preference = normalizePref(localStorage.getItem('theme'));
		// Live-follow the OS while on 'system'.
		this.#mql = window.matchMedia('(prefers-color-scheme: dark)');
		this.#mql.addEventListener('change', () => {
			if (this.preference === 'system') this.#resolveAndApply();
		});
		this.#resolveAndApply();
	}

	set(pref: ThemePref) {
		this.preference = pref;
		if (browser) localStorage.setItem('theme', pref);
		this.#resolveAndApply();
	}

	#resolveAndApply() {
		this.current =
			this.preference === 'system'
				? this.#systemDark()
					? 'dark'
					: 'light'
				: this.preference;
		this.#apply();
	}

	#systemDark(): boolean {
		return !!this.#mql?.matches;
	}

	#apply() {
		if (!browser) return;
		document.documentElement.setAttribute('data-theme', this.current);
		this.refreshChrome();
	}

	/** Re-colour the browser chrome for the applied theme AND palette — the
	 *  palette store calls this when only the palette changes. Sepia keeps its
	 *  own ground under every palette (app.css), so its colour is the theme's. */
	refreshChrome() {
		if (!browser) return;
		const pal = normalizePalette(document.documentElement.dataset.palette);
		const color = this.current === 'sepia' ? THEME_COLOR.sepia : PALETTE_COLORS[pal][this.current];
		// All of them, media attribute removed: app.html ships a media-scoped
		// pair for the pre-hydration paint, and an explicit choice has to win
		// over the OS preference those tags key on.
		for (const tc of document.querySelectorAll('meta[name="theme-color"]')) {
			tc.removeAttribute('media');
			tc.setAttribute('content', color);
		}
	}
}

export const theme = new Theme();
