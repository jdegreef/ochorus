import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';

/**
 * i18n completeness guard. Keeps the four locales honest so a missing key or a
 * left-behind English string can't ship silently:
 *  1. every locale defines exactly the same keys (parity),
 *  2. every `t('…')` key used in the app exists in the base locale,
 *  3. no non-English value is identical to English (i.e. actually translated),
 *     apart from a small allowlist of borrowed / proper-noun terms.
 */

const LOCALES = ['en', 'es', 'sw', 'lg', 'pt', 'ar', 'hi', 'uk'] as const;
const BASE = 'en';
const MSG_DIR = path.resolve('messages');

const load = (l: string): Record<string, string> =>
	JSON.parse(fs.readFileSync(path.join(MSG_DIR, `${l}.json`), 'utf8'));
const data = Object.fromEntries(LOCALES.map((l) => [l, load(l)])) as Record<
	string,
	Record<string, string>
>;
const keysOf = (l: string) => Object.keys(data[l]).filter((k) => k !== '$schema');

// Terms deliberately identical to English across locales: typography names and
// (in Spanish) "Normal". Anything else identical to English is untranslated.
// The settings page repeats several of these under `settings_*` keys.
const SAME_AS_ENGLISH_OK = new Set([
	'font_serif',
	'font_sans',
	'font_dyslexic',
	'spacing_normal',
	'width_normal',
	'settings_font_serif',
	'settings_font_sans',
	'settings_width_normal',
	'common_min',
	'login_email',
	// "Original" is the same word in Spanish — a legitimate borrowed term.
	'reader_original',
	// "A–Z" is the same alphabetical-sort label in every language we support.
	'search_sort_title',
	// "Sepia" is the borrowed colour-tone name, unchanged across our locales.
	'settings_theme_sepia',
	// "Menu" is the natural UI term in Portuguese too (Spanish keeps its accent,
	// "Menú", so this only exempts the pt collision).
	'a11y_menu'
]);

/**
 * Strings a locale has NOT translated yet — declared, rather than hidden.
 *
 * Different in kind from SAME_AS_ENGLISH_OK above, which is "identical to
 * English forever, and correctly so". This is debt, with a reason and a way out.
 *
 * Asserted EXACTLY, in both directions: a fifth untranslated string fails, and
 * so does fixing one of these four without deleting it from here. A pending
 * list that only ever grows is how "temporary" becomes permanent — same
 * two-way ratchet the English-audit baseline uses, for the same reason.
 */
const PENDING_TRANSLATION: Record<string, readonly string[]> = {
	// Empty, and worth keeping that way. uk's four Scripture strings lived here
	// until the Kulish text could be sourced; it now can be, from the ebible
	// USFM mirror on raw.githubusercontent.com, which is reachable where
	// api.takeroot.bible is not. The mechanism stays because the next locale
	// will hit the same wall — the point is that a blocked string is declared
	// and ratcheted rather than quietly allowlisted forever.
};

const toSnake = (key: string) =>
	key
		.replace(/([a-z0-9])([A-Z])/g, '$1_$2')
		.replace(/\./g, '_')
		.toLowerCase();

function usedKeys(): Set<string> {
	const out = new Set<string>();
	const re = /\bt\(\s*['"`]([a-zA-Z0-9_.]+)['"`]\s*\)/g;
	const walk = (dir: string) => {
		for (const name of fs.readdirSync(dir)) {
			const p = path.join(dir, name);
			const stat = fs.statSync(p);
			if (stat.isDirectory()) {
				if (!p.includes('paraglide')) walk(p);
			} else if (/\.(svelte|ts)$/.test(name) && !name.endsWith('.test.ts')) {
				const src = fs.readFileSync(p, 'utf8');
				for (let m; (m = re.exec(src)); ) out.add(toSnake(m[1]));
			}
		}
	};
	walk(path.resolve('src'));
	return out;
}

describe('i18n messages', () => {
	it('all locales define the same keys (parity)', () => {
		const base = new Set(keysOf(BASE));
		for (const l of LOCALES.filter((x) => x !== BASE)) {
			const here = new Set(keysOf(l));
			const missing = [...base].filter((k) => !here.has(k));
			const extra = [...here].filter((k) => !base.has(k));
			expect({ locale: l, missing, extra }).toEqual({ locale: l, missing: [], extra: [] });
		}
	});

	it('every t() key used in the app exists in the base locale', () => {
		const base = new Set(keysOf(BASE));
		const missing = [...usedKeys()].filter((k) => !base.has(k)).sort();
		expect(missing).toEqual([]);
	});

	it('non-English strings are actually translated (or declared pending)', () => {
		// DERIVED from LOCALES, not a second hardcoded list. This check used to
		// carry its own copy of the locale array, which meant every new locale had
		// to be remembered in two places to be covered — and href.test.ts already
		// records what that costs: its locale list was literal, pt was wired in,
		// and the guard silently stopped covering /pt/. One list, one place.
		for (const l of LOCALES.filter((x) => x !== BASE)) {
			const untranslated = keysOf(BASE)
				.filter((k) => !SAME_AS_ENGLISH_OK.has(k) && data[l][k] === data[BASE][k])
				.sort();
			expect(
				{ locale: l, untranslated },
				`${l} has untranslated strings that are not declared in PENDING_TRANSLATION. ` +
					'Translate them, or — if they are blocked on something (a Bible text, a ' +
					'reviewer) — add them there with the reason. If a listed key is now ' +
					'translated, delete it from PENDING_TRANSLATION.'
			).toEqual({ locale: l, untranslated: [...(PENDING_TRANSLATION[l] ?? [])].sort() });
		}
	});
});
