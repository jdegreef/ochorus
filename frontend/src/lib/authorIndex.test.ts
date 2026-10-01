import { describe, expect, it } from 'vitest';
import { authorIndex, filingKey, filingName, filterIndex, foldEditions, indexRows, initialOf } from './authorIndex';

const author = (slug: string, name: string) => ({
	slug,
	name,
	birth_year: null,
	death_year: null
});
const book = (slug: string, title: string, a: string) => ({
	slug,
	title,
	author: author(a, a)
});

describe('initialOf', () => {
	it('files a name under its first letter, accents folded', () => {
		expect(initialOf('Andrew Murray')).toBe('A');
		expect(initialOf('  étienne')).toBe('E');
		expect(initialOf('Ángel')).toBe('A');
		expect(initialOf('1st Writer')).toBe('#');
	});
});

describe('filingName', () => {
	it('files a person under the surname', () => {
		expect(filingName('A. W. Tozer')).toBe('Tozer, A. W.');
		expect(filingName('Charles H. Spurgeon')).toBe('Spurgeon, Charles H.');
		expect(filingName('Martyn Lloyd-Jones')).toBe('Lloyd-Jones, Martyn');
	});

	it('keeps a lowercase particle with the surname and skips a generational suffix', () => {
		expect(filingName('Corrie ten Boom')).toBe('ten Boom, Corrie');
		expect(filingName('Martin Luther King Jr.')).toBe('King, Martin Luther');
	});

	it('files an epithet name or a single name as written', () => {
		expect(filingName('Augustine of Hippo')).toBe('Augustine of Hippo');
		expect(filingName('Gregory the Great')).toBe('Gregory the Great');
		expect(filingName('Thomas à Kempis')).toBe('Thomas à Kempis');
		expect(filingName('Thomas a Kempis')).toBe('Thomas a Kempis');
		expect(filingName('John Of God')).toBe('John Of God');
		expect(filingName('Athanasius')).toBe('Athanasius');
	});
});

describe('filingKey', () => {
	it('drops apostrophes but keeps the surname boundary', () => {
		expect(filingKey('Robert Murray M’Cheyne')).toBe('MCheyne, Robert Murray');
		const order = ['Zoe Smith', 'Al Smithers', 'William Law', 'Brother Lawrence'].sort((a, b) =>
			filingKey(a).localeCompare(filingKey(b), 'en', { sensitivity: 'base' })
		);
		expect(order).toEqual(['William Law', 'Brother Lawrence', 'Zoe Smith', 'Al Smithers']);
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

	it('groups every writer by the initial of their filing name, in order', () => {
		expect(groups.map((g) => [g.letter, g.entries.map((e) => e.author.slug)])).toEqual([
			['A', ['augustine']],
			['B', ['bounds']],
			['M', ['murray']]
		]);
	});

	it("lists each writer's books by title, and keeps a writer with none", () => {
		expect(groups[2].entries[0].books.map((b) => b.slug)).toEqual(['humility', 'with-christ']);
		expect(groups[0].entries[0].books).toEqual([]);
	});

	it('leaves out a skipped slug (the imprint)', () => {
		expect(groups.flatMap((g) => g.entries).some((e) => e.author.slug === 'house')).toBe(false);
	});
});

describe('authorIndex completeness', () => {
	it("adds a book's writer the writers list left out, so no book goes missing", () => {
		const groups = authorIndex([author('murray', 'Andrew Murray')], [book('pulse', 'Pulse', 'hannah')]);
		const all = groups.flatMap((g) => g.entries);
		expect(all.map((e) => e.author.slug)).toEqual(['hannah', 'murray']);
		expect(all[0].books.map((b) => b.slug)).toEqual(['pulse']);
	});
});

describe('foldEditions', () => {
	const b = (slug: string, title: string) => book(slug, title, 'smith');

	it('folds teens and children editions under their full text, teens first', () => {
		const rows = foldEditions([
			b('amanda-smith-autobiography-teens', 'Amanda Smith: An Autobiography (For Teens)'),
			b('amanda-smith-autobiography', 'An Autobiography'),
			b('amanda-smith-autobiography-children', 'The Story of Amanda Smith (For Children)')
		]);
		expect(rows.map((r) => r.book.slug)).toEqual(['amanda-smith-autobiography']);
		expect(rows[0].editions.map((e) => [e.book.slug, e.audience])).toEqual([
			['amanda-smith-autobiography-teens', 'For Teens'],
			['amanda-smith-autobiography-children', 'For Children']
		]);
	});

	it('keeps an edition whose full text is not in the list as its own line, and one with no "(For …)" to label a chip', () => {
		const rows = foldEditions([
			b('the-body-of-christ-a-reality', 'The Body of Christ: A Reality'),
			b('the-body-of-christ-teens', 'The Body of Christ (For Teens)'),
			b('divine-songs-for-children', 'Divine Songs for Children'),
			b('the-body-of-christ-a-reality-children', 'The Body of Christ Retold')
		]);
		expect(rows.map((r) => r.book.slug)).toEqual([
			'the-body-of-christ-a-reality',
			'the-body-of-christ-teens',
			'divine-songs-for-children',
			'the-body-of-christ-a-reality-children'
		]);
		expect(rows.every((r) => r.editions.length === 0)).toBe(true);
	});
});

describe('filterIndex', () => {
	const groups = indexRows(
		authorIndex(
			[author('murray', 'Andrew Murray'), author('muller', 'George Müller')],
			[
				book('humility', 'Humility', 'murray'),
				book('with-christ', 'With Christ in the School of Prayer', 'murray'),
				book('life-of-trust', 'The Life of Trust', 'muller'),
				book('life-of-trust-teens', 'The Life of Trust (For Teens)', 'muller')
			]
		)
	);
	const slugs = (q: string) =>
		filterIndex(groups, q).flatMap((g) => g.entries.map((e) => [e.author.slug, e.rows.map((r) => r.book.slug)]));

	it('returns everything for a blank query', () => {
		expect(filterIndex(groups, '  ')).toBe(groups);
	});

	it('matches a typed apostrophe against a curly one', () => {
		const g = indexRows(authorIndex([], [book('pp', 'The Pilgrim’s Progress', 'bunyan')]));
		expect(filterIndex(g, "pilgrim's")).toHaveLength(1);
	});

	it('keeps every book of a writer whose name matches, accents folded', () => {
		expect(slugs('MULLER')).toEqual([['muller', ['life-of-trust']]]);
	});

	it('keeps only the matching books of other writers, and drops empty letters', () => {
		expect(slugs('humil')).toEqual([['murray', ['humility']]]);
		expect(filterIndex(groups, 'humil').map((g) => g.letter)).toEqual(['M']);
	});

	it("matches an edition's own title and keeps its parent row", () => {
		expect(slugs('for teens')).toEqual([['muller', ['life-of-trust']]]);
	});

	it('returns no groups when nothing matches', () => {
		expect(filterIndex(groups, 'zzz')).toEqual([]);
	});
});
