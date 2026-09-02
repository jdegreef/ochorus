import { describe, expect, it } from 'vitest';
import { BIBLE_CREDIT, bibleCredit, creditParts } from './bibleCredit';
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
		for (const l of ['en', 'es', 'sw', 'pt', 'ar', 'uk']) expect(bibleCredit(l)).toBe('');
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

	it('every credit links its licence, which CC BY-SA actually asks for', () => {
		// §3(a)(1)(A)(iii): supply the URI "if practicable". It is always
		// practicable in an HTML footer, so a credit without one is a bug here.
		for (const [l, credit] of Object.entries(BIBLE_CREDIT)) {
			expect(creditParts(credit).some((p) => p.href), `${l} links no licence`).toBe(true);
		}
	});

	it('splits a credit into text and link runs without losing a character', () => {
		const credit = bibleCredit('hi');
		const parts = creditParts(credit);
		expect(parts.map((p) => p.text).join('')).toBe(credit);
		expect(parts.filter((p) => p.href).map((p) => p.href)).toEqual([
			'https://creativecommons.org/licenses/by-sa/4.0/'
		]);
	});

	it('leaves a credit with no URL as a single run', () => {
		expect(creditParts('Public domain, no link.')).toEqual([{ text: 'Public domain, no link.' }]);
		expect(creditParts('')).toEqual([]);
	});

	it('every credit names a licence — a line that credits nothing is not a credit', () => {
		for (const [l, credit] of Object.entries(BIBLE_CREDIT)) {
			expect(credit.trim(), `${l} credit is empty`).not.toBe('');
			expect(credit, `${l} credit names no licence`).toMatch(/CC |Creative Commons|©/);
		}
	});
});
