import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { footerLocales } from './footerLocales';
import { ADVERTISED_LOCALES } from './advertised-locales';

const entry = (code: string) => ({ code });

describe('the footer language strip', () => {
	it('lists the advertised locales', () => {
		const listed = footerLocales([...ADVERTISED_LOCALES].map(entry), 'en').map((l) => l.code);
		expect(listed).toEqual([...ADVERTISED_LOCALES]);
	});

	it('omits a wired but unadvertised locale the reader is not in', () => {
		// The whole point of the filter: a fully translated interface wrapped
		// around an empty library is a worse first impression than not offering
		// the language at all.
		const listed = footerLocales([entry('en'), entry('zz')], 'en').map((l) => l.code);
		expect(listed).toEqual(['en']);
	});

	it('always lists the locale the reader is actually in', () => {
		// This was the bug. On /hi — a wired UI locale that is not live — the
		// strip named the five advertised languages and not Hindi, so the
		// `aria-current` branch never fired and there was no "you are here" at
		// all. A reader could not tell, from the one control on the page whose
		// job is to say what language they are in, what language they were in.
		const listed = footerLocales([entry('en'), entry('zz')], 'zz').map((l) => l.code);
		expect(listed).toContain('zz');
	});

	it('does not duplicate the current locale when it is also advertised', () => {
		const listed = footerLocales([entry('en'), entry('es')], 'en').map((l) => l.code);
		expect(listed).toEqual(['en', 'es']);
	});

	it('keeps the order it was given, so the strip is stable across locales', () => {
		// Rendered with `{#each ... (l.code)}`; reordering per current locale
		// would make the same list read differently on every page.
		const codes = ['en', 'es', 'sw'].map(entry);
		expect(footerLocales(codes, 'sw').map((l) => l.code)).toEqual(['en', 'es', 'sw']);
	});
});

describe('the two locale lists agree', () => {
	// Every LIVE locale must also be a compiled UI locale, or `localizeHref`
	// cannot build a URL for it — the sitemap and hreflang would publish paths
	// the router does not serve, while the footer silently dropped the locale.
	//
	// `scripts/fetch-live-locales.mjs` already fails the BUILD on this. It runs
	// only when the API is reachable, though, and the generated list it guards is
	// committed — imported by type-checking and by every test in this suite long
	// before a build happens. This asserts the committed file, in CI, with no
	// network.
	const uiLocales: string[] = JSON.parse(
		readFileSync(join(resolve(process.cwd()), 'project.inlang', 'settings.json'), 'utf-8')
	).locales;

	it('finds the UI locale list at all', () => {
		// Guards the guard: a settings.json reshape would otherwise make the
		// assertion below vacuously pass against an empty array.
		expect(uiLocales).toContain('en');
		expect(uiLocales.length).toBeGreaterThan(1);
	});

	it('has a compiled UI locale for every advertised locale', () => {
		const unwired = ADVERTISED_LOCALES.filter((l) => !uiLocales.includes(l));
		expect(
			unwired,
			`advertised with no UI locale: ${unwired.join(', ')} — add them to ` +
				'project.inlang/settings.json (and messages/<code>.json), or set the ' +
				'language back to draft in the admin.'
		).toEqual([]);
	});
});
