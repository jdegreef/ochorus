import { describe, expect, it } from 'vitest';
import { matchBooks, passageSuggestions, quickPassages } from './biblePassage';
import { bookChapterPath } from './reading-schema';

// Hub summaries: chapter_count is the Bible's chapters + an introduction and a conclusion.
const book = (slug: string, title: string, series_position: number, chapters: number) => ({
	slug,
	title,
	series_position,
	chapter_count: chapters + 2
});
const BOOKS = [
	book('psalms', 'The Psalms', 19, 150),
	book('proverbs', 'Proverbs', 20, 31),
	book('philippians', 'Philippians', 50, 4),
	book('philemon', 'Philemon', 57, 1),
	book('romans', 'Romans', 45, 16),
	book('1-corinthians', '1 Corinthians', 46, 16),
	book('gospel-of-john', 'The Gospel of John', 43, 21),
	book('1-john', '1 John', 62, 5)
];

describe('quickPassages', () => {
	it('offers the chips whose book and chapter the library has, in order', () => {
		expect(quickPassages(BOOKS).map((p) => p.label)).toEqual([
			'John 3',
			'Psalm 23',
			'Romans 8',
			'1 Corinthians 13'
		]);
		expect(quickPassages(BOOKS)[1].href).toBe(bookChapterPath('psalms', 24, false));
	});

	it('leaves out a chip the book is too short for', () => {
		expect(quickPassages([book('psalms', 'The Psalms', 19, 20)])).toEqual([]);
	});
});

describe('matchBooks', () => {
	it('matches names and abbreviations by their start, in canon order', () => {
		expect(matchBooks('ph')).toEqual([50, 57]);
		expect(matchBooks('Ps')).toEqual([19]);
		expect(matchBooks('1 cor')).toEqual([46]);
		expect(matchBooks('1cor.')).toEqual([46]);
		expect(matchBooks('jn')).toEqual([43]);
	});

	it('forgives a typo in a longer name', () => {
		expect(matchBooks('Roamns')).toEqual([45]);
		expect(matchBooks('Phillipians')).toEqual([50]);
	});

	it('does not guess at short or unrelated words', () => {
		expect(matchBooks('xq')).toEqual([]);
		expect(matchBooks('grace')).toEqual([]);
	});
});

describe('passageSuggestions', () => {
	it('suggests the chapter, at the verse', () => {
		expect(passageSuggestions('ps 23', BOOKS)).toEqual([
			{ label: 'Psalm 23', href: bookChapterPath('psalms', 24, false) }
		]);
		expect(passageSuggestions('Romans 8:28', BOOKS)).toEqual([
			{ label: 'Romans 8:28', href: `${bookChapterPath('romans', 9, false)}#v28` }
		]);
		expect(passageSuggestions('rom 8.1', BOOKS)[0].label).toBe('Romans 8');
	});

	it('suggests every book a name could mean that has the chapter', () => {
		expect(passageSuggestions('ph 2', BOOKS).map((p) => p.label)).toEqual(['Philippians 2']);
		expect(passageSuggestions('ph 1', BOOKS).map((p) => p.label)).toEqual(['Philippians 1', 'Philemon 1']);
	});

	it("suggests the books' pages for a name alone", () => {
		expect(passageSuggestions('1 j', BOOKS)).toEqual([{ label: '1 John', href: '/books/1-john' }]);
	});

	it('suggests nothing it cannot read, or a book the library lacks', () => {
		expect(passageSuggestions('grace', BOOKS)).toEqual([]);
		expect(passageSuggestions('genesis 1', BOOKS)).toEqual([]);
		expect(passageSuggestions('', BOOKS)).toEqual([]);
		expect(passageSuggestions('john 3 16 17', BOOKS)).toEqual([]);
	});

	it('keeps at most `max`', () => {
		expect(passageSuggestions('p', BOOKS, 2)).toHaveLength(2);
	});
});
