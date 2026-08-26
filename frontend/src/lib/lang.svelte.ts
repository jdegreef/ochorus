import { browser } from '$app/environment';
import type { Language } from './library-public';
import { LIVE_LOCALE_NAMES } from '$lib/live-locales.generated';
import { getLocale, setLocale, locales } from '$lib/paraglide/runtime';

// Set when the reader explicitly picks a language on this device, so a synced
// account profile (see auth.#pullProfile) can't override that choice on the next
// load. Absent on a fresh device, where the profile locale is adopted instead.
const CHOSEN_KEY = 'ochorus:lang';

/**
 * Content language = UI locale, both now driven by the URL prefix (/es, /sw,
 * /lg) via Paraglide. `getLang()` returns the URL's locale and is safe inside
 * SvelteKit `load` functions (server prerender + client), so content fetches
 * (`listBooks(getLang())` etc.) follow the same locale as the chrome.
 *
 * This stays a thin facade over the Paraglide runtime so the many `getLang()` /
 * `lang.*` call sites didn't have to change.
 */

/**
 * Autonyms for every compiled locale — the fallback half of `localeName`.
 *
 * The registry is the source wherever it can speak: `LIVE_LOCALE_NAMES` is
 * generated from it before every build and wins below, so correcting a name in
 * the admin reaches this picker on the next deploy. But it only covers LIVE
 * languages, and the picker offers every *compiled* locale — a reader can
 * switch to one we don't advertise yet (that is the point of the settings
 * switch; see footerLocales). So this stays a COMPLETE list, launched locales
 * included: the generated file lags whatever was last committed, and a name is
 * not worth making conditional on a build having run.
 *
 * Hand-maintained, and safely so: a locale exists only once someone adds it to
 * project.inlang/settings.json and writes messages/<code>.json, so there is
 * always a frontend commit to add the name to. `localeNames.test.ts` fails the
 * build if that commit forgets — which is the failure this replaces, because
 * the old fallback was a bare "hi" in the language picker.
 */
export const LOCALE_NAMES: Record<string, string> = {
	en: 'English',
	es: 'Español',
	sw: 'Kiswahili',
	lg: 'Luganda',
	pt: 'Português',
	ar: 'العربية',
	hi: 'हिन्दी',
	uk: 'Українська'
};

/** The registry's autonym if it has one, else the map above, else the code. */
export const localeName = (code: string): string =>
	LIVE_LOCALE_NAMES[code] ?? LOCALE_NAMES[code] ?? code;

export function getLang(): string {
	return getLocale();
}

const asEntry = (code: string): Language => ({
	code,
	name: localeName(code),
	native_name: localeName(code)
});

// All configured UI locales, computed once (the set is compile-time constant).
const AVAILABLE: Language[] = (locales as readonly string[]).map(asEntry);

class Lang {
	/** All configured UI locales (independent of per-book content availability). */
	get available(): Language[] {
		return AVAILABLE;
	}

	get current(): string {
		return getLocale();
	}

	isAvailable(code: string): boolean {
		return (locales as readonly string[]).includes(code);
	}

	/** Switch locale — navigates to the locale-prefixed URL (full reload). */
	set(code: string): boolean {
		if (code === this.current) return false;
		if (this.isAvailable(code)) setLocale(code as (typeof locales)[number]);
		return true;
	}

	/** The language the reader explicitly chose on this device, if any. */
	chosen(): string | null {
		return browser ? localStorage.getItem(CHOSEN_KEY) : null;
	}

	/** A reader-initiated switch: record the choice so it survives the reload and
	 *  outranks a synced profile locale, then navigate. */
	choose(code: string): boolean {
		if (browser) localStorage.setItem(CHOSEN_KEY, code);
		return this.set(code);
	}

	get currentEntry(): Language {
		return asEntry(this.current);
	}
}

export const lang = new Lang();
