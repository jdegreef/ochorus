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
		expect(quickPassages(BOOKS, 'en').map((p) => p.label)).toEqual([
			'John 3',
			'Psalm 23',
			'Romans 8',
			'1 Corinthians 13'
		]);
		expect(quickPassages(BOOKS, 'en')[1].href).toBe(bookChapterPath('psalms', 24, false));
	});

	it('leaves out a chip the book is too short for', () => {
		expect(quickPassages([book('psalms', 'The Psalms', 19, 20)], 'en')).toEqual([]);
	});
});

describe('matchBooks', () => {
	it('matches names and abbreviations by their start, in canon order', () => {
		expect(matchBooks('ph', 'en')).toEqual([50, 57]);
		expect(matchBooks('Ps', 'en')).toEqual([19]);
		expect(matchBooks('1 cor', 'en')).toEqual([46]);
		expect(matchBooks('1cor.', 'en')).toEqual([46]);
		expect(matchBooks('jn', 'en')).toEqual([43]);
	});

	it('forgives a typo in a longer name', () => {
		expect(matchBooks('Roamns', 'en')).toEqual([45]);
		expect(matchBooks('Phillipians', 'en')).toEqual([50]);
	});

	it('does not guess at short or unrelated words', () => {
		expect(matchBooks('xq', 'en')).toEqual([]);
		expect(matchBooks('grace', 'en')).toEqual([]);
	});
});

describe('passageSuggestions', () => {
	it('suggests the chapter, at the verse', () => {
		expect(passageSuggestions('ps 23', BOOKS, 'en')).toEqual([
			{ label: 'Psalm 23', href: bookChapterPath('psalms', 24, false) }
		]);
		expect(passageSuggestions('Romans 8:28', BOOKS, 'en')).toEqual([
			{ label: 'Romans 8:28', href: `${bookChapterPath('romans', 9, false)}#v28` }
		]);
		expect(passageSuggestions('rom 8.1', BOOKS, 'en')[0].label).toBe('Romans 8');
	});

	it('suggests every book a name could mean that has the chapter', () => {
		expect(passageSuggestions('ph 2', BOOKS, 'en').map((p) => p.label)).toEqual(['Philippians 2']);
		expect(passageSuggestions('ph 1', BOOKS, 'en').map((p) => p.label)).toEqual(['Philippians 1', 'Philemon 1']);
	});

	it("suggests the books' pages for a name alone", () => {
		expect(passageSuggestions('1 j', BOOKS, 'en')).toEqual([{ label: '1 John', href: '/books/1-john' }]);
	});

	it('suggests nothing it cannot read, or a book the library lacks', () => {
		expect(passageSuggestions('grace', BOOKS, 'en')).toEqual([]);
		expect(passageSuggestions('genesis 1', BOOKS, 'en')).toEqual([]);
		expect(passageSuggestions('', BOOKS, 'en')).toEqual([]);
		expect(passageSuggestions('john 3 16 17', BOOKS, 'en')).toEqual([]);
	});

	it('keeps at most `max`', () => {
		expect(passageSuggestions('p', BOOKS, 'en', 2)).toHaveLength(2);
	});
});

describe('in Spanish', () => {
	it('names the quick passages as the Spanish chapters are titled', () => {
		expect(quickPassages(BOOKS, 'es').map((p) => p.label)).toEqual([
			'Juan 3',
			'Salmo 23',
			'Romanos 8',
			'1 Corintios 13'
		]);
	});

	it('reads Spanish names, with or without accents, and the English ones too', () => {
		expect(matchBooks('Juan', 'es')).toEqual([43]);
		expect(matchBooks('Éxodo', 'es')).toEqual([2]);
		expect(matchBooks('exodo', 'es')).toEqual([2]);
		expect(matchBooks('Salmo', 'es')).toEqual([19]);
		expect(matchBooks('Romans', 'es')).toEqual([45]);
		expect(matchBooks('Romnaos', 'es')).toEqual([45]);
	});

	it('leaves a common word to search, rather than a book one typo away', () => {
		const ALL = [...BOOKS, book('amos', 'Amós', 30, 9), book('james', 'Santiago', 59, 5)];
		expect(matchBooks('amor', 'es')).toEqual([30]); // fuzzy: Amós
		expect(passageSuggestions('amor', ALL, 'es')).toEqual([]);
		expect(passageSuggestions('santo', ALL, 'es')).toEqual([]);
		expect(passageSuggestions('Roamns', BOOKS, 'en')).toEqual([]);
		// With a chapter, a typo still reads as a reference.
		expect(passageSuggestions('Romnaos 8', BOOKS, 'es')[0].label).toBe('Romanos 8');
		expect(passageSuggestions('Amós', ALL, 'es')).toEqual([{ label: 'Amós', href: '/books/amos' }]);
	});

	it('suggests Spanish chapters at a verse', () => {
		expect(passageSuggestions('Juan 3:16', BOOKS, 'es')).toEqual([
			{ label: 'Juan 3:16', href: `${bookChapterPath('gospel-of-john', 4, false)}#v16` }
		]);
		expect(passageSuggestions('Salmo 23', BOOKS, 'es')[0].label).toBe('Salmo 23');
		expect(passageSuggestions('Filipenses', BOOKS, 'es')).toEqual([
			{ label: 'Philippians', href: '/books/philippians' }
		]);
	});
});

describe('in French and Portuguese', () => {
	const ALL = [
		...BOOKS,
		book('job', 'Job', 18, 42),
		book('isaiah', 'Isaiah', 23, 66),
		book('amos', 'Amos', 30, 9),
		book('joshua', 'Joshua', 6, 24)
	];

	it('names the quick passages as each edition titles its chapters', () => {
		expect(quickPassages(ALL, 'fr').map((p) => p.label)).toEqual([
			'Jean 3',
			'Psaume 23',
			'Romains 8',
			'1 Corinthiens 13',
			'Ésaïe 53'
		]);
		expect(quickPassages(ALL, 'pt').map((p) => p.label)).toEqual([
			'João 3',
			'Salmo 23',
			'Romanos 8',
			'1 Coríntios 13',
			'Isaías 53'
		]);
	});

	it('reads each language’s names, with or without accents, and the English ones too', () => {
		expect(matchBooks('Ésaïe', 'fr')).toEqual([23]);
		expect(matchBooks('esaie', 'fr')).toEqual([23]);
		expect(matchBooks('Isaïe', 'fr')).toEqual([23]);
		expect(matchBooks('Psaume', 'fr')).toEqual([19]);
		expect(matchBooks('Hé', 'fr')).toEqual([58]);
		expect(matchBooks('Romans', 'fr')).toEqual([45]);
		expect(matchBooks('João', 'pt')).toEqual([43]);
		expect(matchBooks('joao', 'pt')).toEqual([43]);
		expect(matchBooks('Gênesis', 'pt')).toEqual([1]);
		expect(matchBooks('Oséias', 'pt')).toEqual([28]);
		expect(matchBooks('Romans', 'pt')).toEqual([45]);
	});

	it('puts an exact name first: Portuguese "Jo" is João, "Jó" is Job', () => {
		expect(matchBooks('Jo', 'pt')[0]).toBe(43);
		expect(matchBooks('Jó', 'pt')[0]).toBe(18);
		expect(passageSuggestions('Jo 3:16', ALL, 'pt')[0]).toEqual({
			label: 'João 3:16',
			href: `${bookChapterPath('gospel-of-john', 4, false)}#v16`
		});
		expect(passageSuggestions('Jó 38', ALL, 'pt')[0].label).toBe('Jó 38');
	});

	it('leaves a common word to search, rather than a book one typo away', () => {
		for (const [w, lang] of [
			['amour', 'fr'],
			['grâce', 'fr'],
			['amor', 'pt'],
			['graça', 'pt']
		])
			expect(passageSuggestions(w, ALL, lang), w).toEqual([]);
		expect(matchBooks('amor', 'pt')).toEqual([30]); // fuzzy: Amós
		// With a chapter, a typo still reads as a reference.
		expect(passageSuggestions('Romians 8', ALL, 'fr')[0].label).toBe('Romains 8');
		expect(passageSuggestions('Romnaos 8', ALL, 'pt')[0].label).toBe('Romanos 8');
	});

	it('suggests chapters at a verse', () => {
		expect(passageSuggestions('Jean 3:16', ALL, 'fr')).toEqual([
			{ label: 'Jean 3:16', href: `${bookChapterPath('gospel-of-john', 4, false)}#v16` }
		]);
		expect(passageSuggestions('Psaume 23', ALL, 'fr')[0].label).toBe('Psaume 23');
		expect(passageSuggestions('Salmo 23', ALL, 'pt')[0].label).toBe('Salmo 23');
		expect(passageSuggestions('Es 53', ALL, 'fr')[0].label).toBe('Ésaïe 53');
	});
});

describe('in Swahili', () => {
	const ALL = [
		...BOOKS,
		book('isaiah', 'Isaya', 23, 66),
		book('jonah', 'Yona', 32, 4),
		book('gospel-of-matthew', 'Mathayo', 40, 28),
		book('acts-of-the-apostles', 'Matendo', 44, 28)
	];

	it('names the quick passages as the edition titles its chapters', () => {
		expect(quickPassages(ALL, 'sw').map((p) => p.label)).toEqual([
			'Yohana 3',
			'Zaburi 23',
			'Warumi 8',
			'1 Wakorintho 13',
			'Isaya 53',
			'Mathayo 5'
		]);
	});

	it('reads the Swahili names and abbreviations, and the English ones too', () => {
		expect(matchBooks('Zaburi', 'sw')).toEqual([19]);
		expect(matchBooks('Yn', 'sw')[0]).toBe(43);
		expect(matchBooks('Yon', 'sw')[0]).toBe(32);
		expect(matchBooks('Mdo', 'sw')).toEqual([44]);
		expect(matchBooks('Walawi', 'sw')).toEqual([3]);
		expect(matchBooks('Law', 'sw')).toEqual([3]);
		expect(matchBooks('Mwa', 'sw')).toEqual([1]);
		expect(matchBooks('Ufu', 'sw')).toEqual([66]);
		expect(matchBooks('Romans', 'sw')).toEqual([45]);
	});

	it('jumps to a typed chapter, at a verse', () => {
		expect(passageSuggestions('Zaburi 23', ALL, 'sw')[0]).toEqual({
			label: 'Zaburi 23',
			href: bookChapterPath('psalms', 24, false)
		});
		expect(passageSuggestions('Yn 3:16', ALL, 'sw')[0]).toEqual({
			label: 'Yohana 3:16',
			href: `${bookChapterPath('gospel-of-john', 4, false)}#v16`
		});
		expect(passageSuggestions('1 Kor 13', ALL, 'sw')[0].label).toBe('1 Wakorintho 13');
		expect(passageSuggestions('Waroumi 8', ALL, 'sw')[0].label).toBe('Warumi 8');
	});

	it('leaves a common word to search, rather than a book one typo away', () => {
		for (const w of ['upendo', 'neema', 'imani', 'amani', 'maombi', 'Yesu'])
			expect(passageSuggestions(w, ALL, 'sw'), w).toEqual([]);
	});
});
