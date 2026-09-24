import { describe, it, expect } from 'vitest';
import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { ADVERTISED_LOCALES } from './advertised-locales';
// Imported rather than re-implemented: the gate and the generator must compute
// completeness the same way, or one of them is lying.
import { buildSummary } from '../../scripts/sync-ui-catalogues.mjs';

/**
 * Interface-catalogue completeness.
 *
 * Paraglide's base locale is English, so a message key missing from a locale's
 * catalogue silently renders the English string. That is the third way English
 * leaks into a non-English page (the other two — author bios and topic prose —
 * are guarded in the backend by `NoSourceLanguageLeakTests`), and it is the
 * least visible: the page looks fine until a reader of that language finds the
 * one button nobody translated.
 *
 * The bar is deliberately tied to whether a locale is ADVERTISED rather than
 * merely wired up:
 *
 *   - An ADVERTISED locale is one we tell search engines to rank and a reader
 *     is invited into. It must be complete — this test fails the build.
 *   - An unadvertised locale is still being built out. Gaps are expected, so
 *     they are reported, not failed.
 *
 * That mirrors how a language becomes live, and means "go live" can lean on a
 * check that already exists rather than inventing a second definition of ready.
 */

const MESSAGES_DIR = join(process.cwd(), 'messages');

const load = (locale: string): Record<string, string> =>
	JSON.parse(readFileSync(join(MESSAGES_DIR, `${locale}.json`), 'utf-8'));

/** Real message keys — `$schema` is metadata, not a string readers ever see. */
const keysOf = (catalogue: Record<string, string>): Set<string> =>
	new Set(Object.keys(catalogue).filter((k) => !k.startsWith('$')));

/**
 * Each locale's key set, parsed once. The completeness checks test every
 * English key against a catalogue, so calling `keysOf(load(locale))` inside
 * that loop re-read and re-parsed the file once per key — thousands of parses
 * per locale, which walked the suite into vitest's 5s timeout.
 */
const keyCache = new Map<string, Set<string>>();
const keysFor = (locale: string): Set<string> => {
	let keys = keyCache.get(locale);
	if (!keys) keyCache.set(locale, (keys = keysOf(load(locale))));
	return keys;
};

const catalogueLocales = (): string[] =>
	readdirSync(MESSAGES_DIR)
		.filter((f) => f.endsWith('.json'))
		.map((f) => f.replace(/\.json$/, ''))
		.sort();

describe('message catalogues', () => {
	const base = keysFor('en');

	it('has a non-trivial English catalogue to compare against', () => {
		// Guards the guard: a glob or path change that silently loaded {} would
		// make every completeness assertion below vacuously pass.
		expect(base.size).toBeGreaterThan(100);
	});

	it('uses the "— Ochorus" title suffix in every catalogue, never "· Ochorus"', () => {
		// The browser-title brand suffix is " — Ochorus" (em dash) site-wide. The
		// suffix lives inside translatable strings (e.g. book_title_tag), so a
		// per-catalogue "· Ochorus" is invisible until a reader of that language
		// opens a tab — which is exactly how seven catalogues drifted once.
		const offenders = catalogueLocales().filter((loc) =>
			Object.values(load(loc)).some((v) => typeof v === 'string' && v.includes('· Ochorus'))
		);
		expect(
			offenders,
			`These catalogues carry "· Ochorus"; the site suffix is "— Ochorus" (em dash).`
		).toEqual([]);
	});

	for (const locale of ADVERTISED_LOCALES.filter((l) => l !== 'en')) {
		it(`${locale} is complete — it is advertised, so readers are invited into it`, () => {
			const keys = keysFor(locale);
			const missing = [...base].filter((k) => !keys.has(k));
			expect(
				missing,
				`${locale}.json is missing ${missing.length} key(s), which would render in ` +
					`English for a ${locale} reader:\n  ${missing.slice(0, 20).join('\n  ')}` +
					(missing.length > 20 ? `\n  …and ${missing.length - 20} more` : '')
			).toEqual([]);
		});
	}

	it('no catalogue carries keys English does not have', () => {
		// A stale key is dead weight and usually means a rename landed in one
		// catalogue but not the rest.
		for (const locale of catalogueLocales()) {
			const extra = [...keysFor(locale)].filter((k) => !base.has(k));
			expect(extra, `${locale}.json has keys absent from en.json: ${extra.join(', ')}`).toEqual(
				[]
			);
		}
	});

	it('the summary the API reads matches the catalogues', () => {
		// The admin's readiness report says whether a language's interface is
		// translated, and the deployed API cannot see these files — its image is
		// built from backend/ alone. So each locale's missing and pending keys are handed
		// across as a committed JSON file, and this is what stops that file from
		// drifting: a stale summary would report a language ready on the strength
		// of a catalogue that has since grown, which is worse than reporting
		// nothing.
		const committed = readFileSync(
			join(process.cwd(), '..', 'backend', 'library', 'data', 'ui_catalogues.json'),
			'utf-8'
		);
		const expected = JSON.stringify(buildSummary(MESSAGES_DIR), null, '\t') + '\n';
		expect(
			committed,
			'backend/library/data/ui_catalogues.json is out of date — run:\n' +
				'  cd frontend && npm run sync:catalogues'
		).toEqual(expected);
	});

	it('reports completeness for locales that are not yet advertised', () => {
		// Not a failure: these are still being built. Surfacing the number is what
		// makes "is this language ready?" answerable without opening the files.
		const unadvertised = catalogueLocales().filter(
			(l) => !(ADVERTISED_LOCALES as readonly string[]).includes(l)
		);
		for (const locale of unadvertised) {
			const keys = keysFor(locale);
			const present = [...base].filter((k) => keys.has(k)).length;
			const pct = Math.round((present / base.size) * 100);
			console.info(`  ${locale}: ${present}/${base.size} interface strings (${pct}%)`);
			expect(pct).toBeGreaterThanOrEqual(0);
		}
	});
});
