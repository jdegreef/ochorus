import { describe, expect, it } from 'vitest';
import { chapterNumber } from './chapterGrid';

describe('chapterNumber', () => {
	it("reads the Bible's chapter number off the title, not the row order", () => {
		expect(chapterNumber('Genesis 1')).toBe(1);
		expect(chapterNumber('Psalm 150')).toBe(150);
		expect(chapterNumber('1 Corinthians 13')).toBe(13);
		expect(chapterNumber('Song of Songs 8')).toBe(8);
	});

	it('gives the introduction and conclusion (no trailing number) no number', () => {
		expect(chapterNumber('Introduction')).toBeNull();
		expect(chapterNumber('Conclusion')).toBeNull();
		expect(chapterNumber('1 John')).toBeNull();
		expect(chapterNumber('')).toBeNull();
		expect(chapterNumber(null)).toBeNull();
	});
});
