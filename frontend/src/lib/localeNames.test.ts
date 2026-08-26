import { describe, expect, it } from 'vitest';
import { locales } from '$lib/paraglide/runtime';
import { LIVE_LOCALES, LIVE_LOCALE_NAMES } from '$lib/live-locales.generated';
import { LOCALE_NAMES, localeName } from './lang.svelte';

/**
 * Where a language's name in the reader comes from.
 *
 * Two sources, deliberately: the `Language` registry (generated into
 * `live-locales.generated.ts` before every build) for the languages it has
 * launched, and a hand-maintained map for compiled locales it hasn't. The
 * registry wins where both speak, so a name corrected in the admin ships on the
 * next build instead of living on in a frontend constant forever — that map was
 * the last survivor of the four hand-synced language lists described in the
 * Language model's docstring.
 *
 * What the build must never allow is a locale with no name at all. The old
 * fallback was the bare code, so forgetting one shipped a picker offering
 * "hi" — silently, because nothing looks at that list in a language it can't
 * read.
 */
describe('locale names', () => {
	it('names every compiled locale', () => {
		// The gate. A UI locale exists only once someone adds it to
		// project.inlang/settings.json and writes messages/<code>.json — this
		// fails that commit if it forgot the name.
		const unnamed = (locales as readonly string[]).filter((c) => localeName(c) === c);
		expect(unnamed, 'compiled locales with no autonym').toEqual([]);
	});

	it('prefers the registry over the hand-maintained map', () => {
		// Non-vacuous only if a live locale is actually in the generated map.
		const fromRegistry = (LIVE_LOCALES as readonly string[]).filter(
			(c) => c in LIVE_LOCALE_NAMES
		);
		expect(fromRegistry.length).toBeGreaterThan(0);
		for (const code of fromRegistry) {
			expect(localeName(code)).toBe(LIVE_LOCALE_NAMES[code]);
		}
	});

	it('falls back to the map for a compiled locale the registry has not launched', () => {
		const unlaunched = (locales as readonly string[]).filter(
			(c) => !(c in LIVE_LOCALE_NAMES)
		);
		// Today: ar, hi, uk — wired in the UI, not yet advertised. If this set is
		// ever empty the assertion below is vacuous, which is fine: it means the
		// registry covers everything and the map is pure redundancy.
		for (const code of unlaunched) {
			expect(localeName(code)).toBe(LOCALE_NAMES[code]);
		}
	});

	it('falls back to the code for a locale nothing knows about', () => {
		// Not a supported state — just the guarantee that it renders SOMETHING
		// rather than "undefined" in a picker.
		expect(localeName('zz')).toBe('zz');
	});

	it('autonyms are in their own script, not English', () => {
		// The strip exists so a reader who cannot read English finds their
		// language in it. "Spanish" in an English page defeats that; "Español"
		// is the whole point. English is itself, and Luganda's autonym is
		// genuinely "Luganda" — those two are the legitimate Latin-script
		// matches, so they are the only exemptions.
		const englishNames: Record<string, string> = {
			es: 'Spanish',
			sw: 'Swahili',
			pt: 'Portuguese',
			ar: 'Arabic',
			hi: 'Hindi',
			uk: 'Ukrainian'
		};
		for (const [code, english] of Object.entries(englishNames)) {
			if (!(locales as readonly string[]).includes(code)) continue;
			expect(localeName(code), `${code} should be an autonym`).not.toBe(english);
		}
	});
});
