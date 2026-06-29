import { browser } from '$app/environment';
import type { Language } from './library';

/**
 * Selected *content* language — which set of (per-language) Books the reader
 * sees. Distinct from any future UI-string locale, though they default together.
 * Persisted device-local; synced to the profile `locale` when login lands.
 *
 * `getLang()` is a plain synchronous read for use inside SvelteKit `load`
 * functions (which run outside component reactivity); the `lang` store is the
 * reactive view for components.
 */

const KEY = 'ochorus:language';
const DEFAULT = 'en';

export function getLang(): string {
	if (!browser) return DEFAULT;
	return localStorage.getItem(KEY) || DEFAULT;
}

class Lang {
	current = $state(DEFAULT);
	available = $state<Language[]>([{ code: 'en', name: 'English', native_name: 'English' }]);

	init() {
		if (browser) this.current = getLang();
	}

	setAvailable(langs: Language[]) {
		if (langs.length) this.available = langs;
	}

	/** Change content language and persist. Returns true if it actually changed. */
	set(code: string): boolean {
		if (code === this.current) return false;
		this.current = code;
		if (browser) localStorage.setItem(KEY, code);
		return true;
	}

	get currentEntry(): Language {
		return this.available.find((l) => l.code === this.current) ?? this.available[0];
	}
}

export const lang = new Lang();
