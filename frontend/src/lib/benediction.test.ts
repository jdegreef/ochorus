import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import { BLESSINGS } from './benediction.generated';
import { blessingBible, blessingFor, SEASON_BLESSING, type BlessingKey } from './benediction';
import { bibleCredit } from './bibleCredit';
import { locales } from '$lib/paraglide/runtime';

const KEYS: BlessingKey[] = ['aaronic', 'hope', 'keep', 'shepherd', 'grace'];
const table = BLESSINGS as unknown as Record<string, Record<string, { book: string; passage: string; text: string }>>;

describe('benediction', () => {
	it('closes every UI locale, and only real ones, with all five blessings', () => {
		for (const l of locales) expect(l in BLESSINGS, l).toBe(true);
		for (const l of Object.keys(BLESSINGS)) {
			expect(locales as readonly string[]).toContain(l);
			for (const k of KEYS) expect(table[l][k], `${l} ${k}`).toBeTruthy();
		}
	});

	it('turns with the Church year', () => {
		// 2026: Advent from 29 Nov, Easter 5 Apr, Pentecost 24 May.
		const at = (y: number, m: number, d: number) => blessingFor('en', new Date(y, m - 1, d))?.passage;
		expect(at(2026, 12, 6)).toBe('15:13'); // Advent — Romans
		expect(at(2026, 3, 1)).toBe('24–25'); // Lent — Jude
		expect(at(2026, 4, 1)).toBe('24–25'); // Holy Week
		expect(at(2026, 4, 5)).toBe('13:20–21'); // Easter Day — Hebrews
		expect(at(2026, 5, 24)).toBe('13:14'); // Pentecost — 2 Corinthians
		expect(at(2026, 7, 14)).toBe('6:24–26'); // ordinary time — Numbers
		expect(at(2026, 12, 25)).toBe('6:24–26'); // Christmas
		expect(new Set(Object.values(SEASON_BLESSING))).toEqual(new Set(KEYS));
	});

	it('has no blessing for a locale it does not know', () => {
		expect(blessingFor('zz')).toBeNull();
	});

	/**
	 * A licensed Bible quoted on every page owes its credit on every page. The
	 * footer's credit line is that discharge, so a licensed text here without a
	 * credit there would be an obligation silently left undone.
	 */
	it('quotes a licensed Bible only where the footer credits it', () => {
		const licensed = new Set(['irvhin', 'lug', 'am-ulb']);
		for (const l of Object.keys(BLESSINGS)) {
			if (licensed.has(blessingBible(l) ?? '')) expect(bibleCredit(l), l).not.toBe('');
		}
	});

	it('stands alone: trimmed text, no surrounding speech marks, a passage apart from the book', () => {
		for (const [l, row] of Object.entries(table)) {
			for (const k of KEYS) {
				const b = row[k];
				expect(b.text, `${l} ${k}`).toBe(b.text.trim());
				expect(b.text, `${l} ${k}`).not.toMatch(/^[“”‘’"]|[“”‘’"]$/);
				expect(b.text, `${l} ${k}`).not.toMatch(/\s{2}|’ | ’|Ð/);
				expect(b.passage, `${l} ${k}`).toMatch(/^(\d+:)?\d+(–\d+)?$/);
				expect(b.book, `${l} ${k}`).not.toMatch(/\d+:\d/);
			}
		}
	});
});

/**
 * The generator names each locale's Bible by hand; language_seed.py is where
 * that choice is made. #6012 drifted (ebible ids vie1934/kor, which Take Root
 * does not carry, so vi and ko silently got no blessing) — hold them equal.
 * Amharic was added from the admin, so the seed has no entry to compare.
 */
describe('benediction sources', () => {
	it('quotes the Bible language_seed.py names for each locale', () => {
		const seed = readFileSync(join(process.cwd(), '..', 'backend', 'library', 'language_seed.py'), 'utf-8');
		const seeded = new Map<string, string>();
		for (const m of seed.matchAll(/^ {4}"([a-z]{2})": \{[\s\S]*?^ {8}"bible": "([^"]+)"/gm)) seeded.set(m[1], m[2]);
		expect(seeded.size).toBeGreaterThan(5);
		for (const [l, bible] of seeded) expect(blessingBible(l), l).toBe(bible);
	});
});
