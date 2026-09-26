import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
// The generator owns the "untranslated" rule (value identical to English and
// not in scripts/same-as-english.mjs); this test ratchets its answer.
import { buildSummary } from '../../scripts/sync-ui-catalogues.mjs';

/**
 * i18n completeness guard. Keeps the four locales honest so a missing key or a
 * left-behind English string can't ship silently:
 *  1. every locale defines exactly the same keys (parity),
 *  2. every `t('…')` key used in the app exists in the base locale,
 *  3. no non-English value is identical to English (i.e. actually translated),
 *     apart from a small allowlist of borrowed / proper-noun terms.
 */

const LOCALES = ['en', 'es', 'sw', 'lg', 'pt', 'ar', 'hi', 'uk', 'fr', 'am'] as const;
const BASE = 'en';
const MSG_DIR = path.resolve('messages');

const load = (l: string): Record<string, string> =>
	JSON.parse(fs.readFileSync(path.join(MSG_DIR, `${l}.json`), 'utf8'));
const data = Object.fromEntries(LOCALES.map((l) => [l, load(l)])) as Record<
	string,
	Record<string, string>
>;
const keysOf = (l: string) => Object.keys(data[l]).filter((k) => k !== '$schema');

/**
 * Strings a locale has NOT translated yet — declared, rather than hidden.
 *
 * Different in kind from SAME_AS_ENGLISH_OK (scripts/same-as-english.mjs),
 * which is "identical to English forever, and correctly so". This is debt, with a reason and a way out.
 *
 * Asserted EXACTLY, in both directions: a fifth untranslated string fails, and
 * so does fixing one of these four without deleting it from here. A pending
 * list that only ever grows is how "temporary" becomes permanent — same
 * two-way ratchet the English-audit baseline uses, for the same reason.
 */
const PENDING_TRANSLATION: Record<string, readonly string[]> = {
	// A blocked/awaiting-translation string is declared here and ratcheted
	// (asserted exactly, both directions) rather than quietly allowlisted
	// forever. Empty since the ar/hi/lg/sw/uk feedback, Q&A and "more like this"
	// placeholders were translated (2026-09-23); uk's four Scripture strings
	// lived here once too, until the Kulish text could be sourced.
	//
	// Amharic quotes the 1962 UBS Bible (NT revised 2003). Its New Testament is
	// on the ebible mirror (gracious-tech/fetch_collection, bibles/amh_amh), so
	// Matthew 25:36, Colossians 3:16 and John 1:5 are verbatim; the mirror
	// carries no Old Testament, so Isaiah 55:11 waits for a 1962 OT source.
	// Do not paraphrase it.
	am: ['about_scripture1']
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
		const summary = buildSummary(MSG_DIR).locales;
		for (const l of LOCALES.filter((x) => x !== BASE)) {
			const untranslated = summary[l].pending;
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
