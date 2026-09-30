import { describe, expect, it } from 'vitest';
import {
	ADVERTISED_LOCALES,
	UNADVERTISED_LOCALES,
	UNADVERTISED_ROBOTS,
	markUnadvertisedNoindex
} from './advertised-locales';

const page = '<html><head><title>x</title></head><body></body></html>';

describe('markUnadvertisedNoindex', () => {
	it('leaves every advertised locale indexable', () => {
		for (const l of ADVERTISED_LOCALES) expect(markUnadvertisedNoindex(page, l)).toBe(page);
	});

	it('noindexes (but follows) a locale that is not live', () => {
		// Pick any unadvertised UI locale; skip only if every locale is live.
		const l = UNADVERTISED_LOCALES[0];
		if (!l) return;
		const out = markUnadvertisedNoindex(page, l);
		expect(out).toContain(UNADVERTISED_ROBOTS);
		expect(UNADVERTISED_ROBOTS).toContain('follow');
		expect(out.indexOf(UNADVERTISED_ROBOTS)).toBeLessThan(out.indexOf('</head>'));
	});

	it('never stacks a second robots directive on a page that states its own', () => {
		const l = UNADVERTISED_LOCALES[0];
		if (!l) return;
		const own = page.replace('</head>', '<meta name="robots" content="noindex"/></head>');
		expect(markUnadvertisedNoindex(own, l)).toBe(own);
	});
});
