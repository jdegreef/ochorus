import { describe, it, expect } from 'vitest';
import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { ADVERTISED_LOCALES } from './advertised-locales';

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

const catalogueLocales = (): string[] =>
	readdirSync(MESSAGES_DIR)
		.filter((f) => f.endsWith('.json'))
		.map((f) => f.replace(/\.json$/, ''))
		.sort();

describe('message catalogues', () => {
	const base = keysOf(load('en'));

	it('has a non-trivial English catalogue to compare against', () => {
		// Guards the guard: a glob or path change that silently loaded {} would
		// make every completeness assertion below vacuously pass.
		expect(base.size).toBeGreaterThan(100);
	});

	for (const locale of ADVERTISED_LOCALES.filter((l) => l !== 'en')) {
		it(`${locale} is complete — it is advertised, so readers are invited into it`, () => {
			const missing = [...base].filter((k) => !keysOf(load(locale)).has(k));
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
			const extra = [...keysOf(load(locale))].filter((k) => !base.has(k));
			expect(extra, `${locale}.json has keys absent from en.json: ${extra.join(', ')}`).toEqual(
				[]
			);
		}
	});

	it('reports completeness for locales that are not yet advertised', () => {
		// Not a failure: these are still being built. Surfacing the number is what
		// makes "is this language ready?" answerable without opening the files.
		const unadvertised = catalogueLocales().filter(
			(l) => !(ADVERTISED_LOCALES as readonly string[]).includes(l)
		);
		for (const locale of unadvertised) {
			const present = [...base].filter((k) => keysOf(load(locale)).has(k)).length;
			const pct = Math.round((present / base.size) * 100);
			console.info(`  ${locale}: ${present}/${base.size} interface strings (${pct}%)`);
			expect(pct).toBeGreaterThanOrEqual(0);
		}
	});
});
