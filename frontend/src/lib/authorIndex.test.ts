import { describe, expect, it } from 'vitest';
import { authorIndex, initialOf } from './authorIndex';

const author = (slug: string, name: string) => ({ slug, name, birth_year: null, death_year: null });
const book = (slug: string, title: string, a: string) => ({ slug, title, author: author(a, a) });

describe('initialOf', () => {
	it('files a name under its first letter, accents folded', () => {
		expect(initialOf('Andrew Murray')).toBe('A');
		expect(initialOf('  étienne')).toBe('E');
		expect(initialOf('Ángel')).toBe('A');
		expect(initialOf('1st Writer')).toBe('#');
	});
});

describe('authorIndex', () => {
	const groups = authorIndex(
		[
			author('murray', 'Andrew Murray'),
			author('bounds', 'E. M. Bounds'),
			author('augustine', 'Augustine of Hippo'),
			author('house', 'Ochorus Originals')
		],
		[
			book('with-christ', 'With Christ in the School of Prayer', 'murray'),
			book('humility', 'Humility', 'murray'),
			book('power', 'Power Through Prayer', 'bounds'),
			book('orig', 'An Original', 'house')
		],
		'en',
		['house']
	);

	it('groups every writer by initial, in order', () => {
		expect(groups.map((g) => g.letter)).toEqual(['A', 'E']);
		expect(groups[0].entries.map((e) => e.author.slug)).toEqual(['murray', 'augustine']);
	});

	it("lists each writer's books by title, and keeps a writer with none", () => {
		expect(groups[0].entries[0].books.map((b) => b.slug)).toEqual(['humility', 'with-christ']);
		expect(groups[0].entries[1].books).toEqual([]);
	});

	it('leaves out a skipped slug (the imprint)', () => {
		expect(groups.flatMap((g) => g.entries).some((e) => e.author.slug === 'house')).toBe(false);
	});
});

describe('authorIndex completeness', () => {
	it("adds a book's writer the writers list left out, so no book goes missing", () => {
		const groups = authorIndex([author('murray', 'Andrew Murray')], [book('pulse', 'Pulse', 'hannah')]);
		const all = groups.flatMap((g) => g.entries);
		expect(all.map((e) => e.author.slug)).toEqual(['murray', 'hannah']);
		expect(all[1].books.map((b) => b.slug)).toEqual(['pulse']);
	});
});
