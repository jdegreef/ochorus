import { describe, expect, it } from 'vitest';
import { partEnds, partGroups, partLine, partOf, partQualified } from './bookParts';
import { contentsWindow } from './contentsWindow';

const PARTS = [
	{ title: 'Part One', year: 1678, first_chapter: 1 },
	{ title: 'Part Two', year: 1684, subtitle: 'Christiana', first_chapter: 13 }
];
const CHAPTERS = Array.from({ length: 22 }, (_, i) => ({
	order: i + 1,
	title: i === 0 ? 'Apology' : i === 14 ? 'The First Stage' : i === 1 ? 'The First Stage' : `C${i + 1}`
}));

describe('partOf', () => {
	it('finds the last part starting at or before the chapter', () => {
		expect(partOf(PARTS, 1)?.title).toBe('Part One');
		expect(partOf(PARTS, 12)?.title).toBe('Part One');
		expect(partOf(PARTS, 13)?.title).toBe('Part Two');
		expect(partOf(PARTS, 22)?.title).toBe('Part Two');
	});
	it('is null for a book in one piece, or before the first part', () => {
		expect(partOf([], 3)).toBeNull();
		expect(partOf(undefined, 3)).toBeNull();
		expect(partOf([{ title: 'II', first_chapter: 5 }], 2)).toBeNull();
	});
});

describe('partGroups', () => {
	it('splits the chapters into runs by part', () => {
		const groups = partGroups(CHAPTERS, PARTS);
		expect(groups.map((g) => [g.part?.title, g.chapters.length])).toEqual([
			['Part One', 12],
			['Part Two', 10]
		]);
		expect(partEnds(groups)).toEqual([1, 12, 13, 22]);
	});
	it('is one headless group without parts', () => {
		const groups = partGroups(CHAPTERS, undefined);
		expect(groups).toHaveLength(1);
		expect(groups[0].part).toBeNull();
		expect(partEnds(groups)).toEqual([]);
	});
});

describe('the collapsed contents of a book in parts', () => {
	it('keeps every part heading over chapters of its own', () => {
		const orders = CHAPTERS.map((c) => c.order);
		const shown = contentsWindow(orders, null, partEnds(partGroups(CHAPTERS, PARTS)))!;
		expect([...shown].sort((a, b) => a - b)).toEqual([1, 2, 3, 4, 5, 12, 13, 22]);
	});
});

describe('naming', () => {
	it('says which part a repeated title is in', () => {
		expect(partQualified('The First Stage', PARTS[1], true)).toBe('The First Stage (Part Two)');
		expect(partQualified('The First Stage', PARTS[1], false)).toBe('The First Stage');
		expect(partQualified('The First Stage', null, true)).toBe('The First Stage');
	});
	it('heads a part with its year when it has one', () => {
		expect(partLine(PARTS[0])).toBe('Part One · 1678');
		expect(partLine({ title: 'Book II' })).toBe('Book II');
	});
});
