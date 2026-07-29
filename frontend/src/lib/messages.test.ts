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

const LOCALES = ['en', 'es', 'sw', 'lg', 'pt', 'ar'] as const;
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

	it('non-English strings are actually translated (or allowlisted)', () => {
		for (const l of ['es', 'sw', 'lg', 'pt', 'ar']) {
			const untranslated = keysOf(BASE).filter(
				(k) => !SAME_AS_ENGLISH_OK.has(k) && data[l][k] === data[BASE][k]
			);
			expect({ locale: l, untranslated }).toEqual({ locale: l, untranslated: [] });
		}
	});
});
