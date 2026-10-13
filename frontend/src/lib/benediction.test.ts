import { describe, expect, it } from 'vitest';
import { BENEDICTION } from './benediction';
import { bibleCredit } from './bibleCredit';
import { locales } from '$lib/paraglide/runtime';

describe('benediction', () => {
	it('closes every UI locale, and only real locales', () => {
		for (const l of locales) expect(l in BENEDICTION, l).toBe(true);
		for (const l of Object.keys(BENEDICTION)) expect(locales as readonly string[]).toContain(l);
	});

	/**
	 * A licensed Bible quoted on every page owes its credit on every page. The
	 * footer's credit line is that discharge, so a licensed text here without a
	 * credit there would be an obligation silently left undone.
	 */
	it('quotes a licensed Bible only where the footer credits it', () => {
		const licensed = new Set(['irvhin', 'lug', 'am-ulb']);
		for (const [l, b] of Object.entries(BENEDICTION)) {
			if (licensed.has(b.bible)) expect(bibleCredit(l), l).not.toBe('');
		}
	});

	it('stands alone: three trimmed verses, none still inside Moses’ quotation marks', () => {
		for (const [l, b] of Object.entries(BENEDICTION)) {
			expect(b.lines, l).toHaveLength(3);
			expect(b.book, l).not.toMatch(/\d:\d/);
			for (const line of b.lines) {
				expect(line, l).toBe(line.trim());
				expect(line, l).not.toMatch(/^[“”‘’"]|[“”‘’"]$/);
				expect(line, l).not.toMatch(/\s{2}|’ | ’/);
				// Ð (U+00D0) is Icelandic; Take Root's Cadman uses it for Đ.
				expect(line, l).not.toContain('\u00d0');
			}
		}
	});
});
