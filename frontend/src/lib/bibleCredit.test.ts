import { describe, expect, it } from 'vitest';
import { BIBLE_CREDIT, bibleCredit } from './bibleCredit';
import { locales } from '$lib/paraglide/runtime';

describe('bibleCredit', () => {
	it('credits Hindi, whose Bible is the one licensed text in the library', () => {
		const hi = bibleCredit('hi');
		expect(hi).toContain('Indian Revised Version');
		expect(hi).toContain('Bridge Connectivity Solutions');
		expect(hi).toContain('CC BY-SA 4.0');
	});

	it('says nothing for a public-domain Bible, or an unknown locale', () => {
		// The normal case. KJV, Van Dyck, Kulish and Almeida owe no credit, and a
		// footer line saying so anyway would be noise on every page of the site.
		for (const l of ['en', 'es', 'sw', 'lg', 'pt', 'ar', 'uk']) expect(bibleCredit(l)).toBe('');
		expect(bibleCredit('zz')).toBe('');
	});

	/**
	 * A credit for a locale the site cannot route to is a credit nobody sees.
	 * This is the failure that would be silent: the map is keyed by string, so a
	 * typo ("hin") type-checks, renders nothing, and leaves the obligation
	 * undischarged while looking discharged in the diff.
	 */
	it('only credits locales the site actually has', () => {
		const unknown = Object.keys(BIBLE_CREDIT).filter(
			(l) => !(locales as readonly string[]).includes(l)
		);
		expect(unknown).toEqual([]);
	});

	it('every credit names a licence — a line that credits nothing is not a credit', () => {
		for (const [l, credit] of Object.entries(BIBLE_CREDIT)) {
			expect(credit.trim(), `${l} credit is empty`).not.toBe('');
			expect(credit, `${l} credit names no licence`).toMatch(/CC |Creative Commons|©/);
		}
	});
});
