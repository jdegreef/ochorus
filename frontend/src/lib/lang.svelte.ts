import type { Language } from './library';
import { getLocale, setLocale, locales } from '$lib/paraglide/runtime';

/**
 * Content language = UI locale, both now driven by the URL prefix (/es, /sw,
 * /lg) via Paraglide. `getLang()` returns the URL's locale and is safe inside
 * SvelteKit `load` functions (server prerender + client), so content fetches
 * (`listBooks(getLang())` etc.) follow the same locale as the chrome.
 *
 * This stays a thin facade over the Paraglide runtime so the many `getLang()` /
 * `lang.*` call sites didn't have to change.
 */

/** Native names for the picker; a locale not listed falls back to its code. */
export const LOCALE_NAMES: Record<string, string> = {
	en: 'English',
	es: 'Español',
	sw: 'Kiswahili',
	lg: 'Luganda'
};

export function getLang(): string {
	return getLocale();
}

const asEntry = (code: string): Language => ({
	code,
	name: LOCALE_NAMES[code] ?? code,
	native_name: LOCALE_NAMES[code] ?? code
});

class Lang {
	/** All configured UI locales (independent of per-book content availability). */
	get available(): Language[] {
		return (locales as readonly string[]).map(asEntry);
	}

	get current(): string {
		return getLocale();
	}

	/** No-op: locale is URL-driven. Kept so existing init() calls still resolve. */
	init() {}

	/** Content-availability list is no longer used to gate the picker. */
	setAvailable(_langs: Language[]) {}

	isAvailable(code: string): boolean {
		return (locales as readonly string[]).includes(code);
	}

	/** Switch locale — navigates to the locale-prefixed URL (full reload). */
	set(code: string): boolean {
		if (code === this.current) return false;
		if (this.isAvailable(code)) setLocale(code as (typeof locales)[number]);
		return true;
	}

	get currentEntry(): Language {
		return asEntry(this.current);
	}
}

export const lang = new Lang();
