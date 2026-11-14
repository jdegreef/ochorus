import { describe, expect, it } from 'vitest';
import {
	BIBLE_DIVISIONS,
	BIBLE_STARTS,
	bibleChapterCount,
	bibleChapters,
	canonName,
	biblePlans,
	bibleStarts,
	mayBePassage,
	passageHref,
	canonStrip,
	divisionKey,
	divisionOf,
	groupBible,
	isBibleBook,
	splitBible,
	testamentKey
} from './bible';
import { bookChapterPath } from './reading-schema';
import en from '../../messages/en.json';

const book = (slug: string, series_position: number | null) => ({ slug, series_position });

describe('BIBLE_DIVISIONS', () => {
	it('places every canonical number 1–66 in exactly one division, in order', () => {
		const numbers = BIBLE_DIVISIONS.flatMap((d) =>
			Array.from({ length: d.last - d.first + 1 }, (_, i) => d.first + i)
		);
		expect(numbers).toEqual(Array.from({ length: 66 }, (_, i) => i + 1));
	});

	it('puts Malachi (39) last in the Old Testament and Matthew (40) first in the New', () => {
		expect(divisionOf(39)?.testament).toBe('old');
		expect(divisionOf(40)?.testament).toBe('new');
		expect(divisionOf(44)?.id).toBe('acts');
		expect(divisionOf(66)?.id).toBe('revelation');
		expect(divisionOf(0)).toBeNull();
		expect(divisionOf(67)).toBeNull();
		expect(divisionOf(null)).toBeNull();
	});

	it('has a heading string for every division and both testaments', () => {
		const snake = (k: string) =>
			k.replace(/([a-z0-9])([A-Z])/g, '$1_$2').replace(/\./g, '_').toLowerCase();
		const keys = [
			...BIBLE_DIVISIONS.map((d) => divisionKey(d.id)),
			testamentKey('old'),
			testamentKey('new')
		].map(snake);
		for (const k of keys) expect(en, k).toHaveProperty(k);
	});
});

describe('groupBible', () => {
	it('groups today’s four books under the divisions that have one, in canonical order', () => {
		const groups = groupBible([
			book('romans', 45),
			book('gospel-of-john', 43),
			book('psalms', 19),
			book('genesis', 1)
		]);
		expect(
			groups.map((t) => ({
				testament: t.testament,
				divisions: t.divisions.map((d) => [d.division.id, d.books.map((b) => b.slug)])
			}))
		).toEqual([
			{
				testament: 'old',
				divisions: [
					['law', ['genesis']],
					['wisdom', ['psalms']]
				]
			},
			{
				testament: 'new',
				divisions: [
					['gospels', ['gospel-of-john']],
					['paul', ['romans']]
				]
			}
		]);
	});

	it('shows only the New Testament when no Old Testament book is in', () => {
		const groups = groupBible([book('revelation', 66), book('acts', 44), book('matthew', 40)]);
		expect(groups.map((t) => t.testament)).toEqual(['new']);
		expect(groups[0].divisions.map((d) => d.division.id)).toEqual(['gospels', 'acts', 'revelation']);
	});

	it('orders the books inside a division by their canonical number', () => {
		const [nt] = groupBible([book('mark', 41), book('john', 43), book('matthew', 40), book('luke', 42)]);
		expect(nt.divisions[0].books.map((b) => b.slug)).toEqual(['matthew', 'mark', 'luke', 'john']);
	});

	it('leaves out a book with no place in the canon, and is empty for none', () => {
		expect(groupBible([book('stray', null), book('far', 70)])).toEqual([]);
		expect(groupBible([])).toEqual([]);
	});
});

describe('biblePlans', () => {
	it('offers the named Bible plans that shipped, in their own order', () => {
		const plans = [{ slug: 'psalms-in-150-days' }, { slug: 'romans-with-moule' }, { slug: 'john-in-21-days' }];
		expect(biblePlans(plans).map((p) => p.slug)).toEqual(['john-in-21-days', 'psalms-in-150-days']);
		expect(biblePlans([{ slug: 'romans-with-moule' }])).toEqual([]);
	});

	it('leads with the whole-Bible plans', () => {
		const plans = [
			{ slug: 'john-in-21-days' },
			{ slug: 'new-testament-in-90-days' },
			{ slug: 'bible-in-a-year' },
			{ slug: 'the-story-of-the-bible' }
		];
		expect(biblePlans(plans).map((p) => p.slug)).toEqual([
			'the-story-of-the-bible',
			'bible-in-a-year',
			'new-testament-in-90-days',
			'john-in-21-days'
		]);
	});
});

describe('canonName', () => {
	it('names a canon position, and nothing off it', () => {
		expect(canonName(1)).toBe('Genesis');
		expect(canonName(66)).toBe('Revelation');
		expect([canonName(0), canonName(67), canonName(null)]).toEqual([null, null, null]);
	});
});

describe('bibleChapters', () => {
	it('numbers the Bible chapters, past the introduction', () => {
		const chs = bibleChapters({ slug: 'ruth', title: 'Ruth', chapter_count: 6, series_position: 8 });
		expect(chs.map((c) => c.n)).toEqual([1, 2, 3, 4]);
		expect(chs[0]).toEqual({ n: 1, name: 'Ruth 1', href: bookChapterPath('ruth', 2, false) });
		expect(chs[3].href).toBe(bookChapterPath('ruth', 5, false));
	});

	it('names a chip as the chapter is titled: the canon short name, "Psalm", or the title off the canon', () => {
		const psalms = bibleChapters({ slug: 'psalms', title: 'The Psalms', chapter_count: 152, series_position: 19 });
		expect(psalms[22].name).toBe('Psalm 23');
		expect(bibleChapters({ slug: 'x', title: 'Stray', chapter_count: 3, series_position: null })[0].name).toBe(
			'Stray 1'
		);
	});

	it('is empty for a book with no Bible chapters', () => {
		expect(bibleChapters({ slug: 'x', title: 'X', chapter_count: 2, series_position: 1 })).toEqual([]);
		expect(bibleChapters({ slug: 'x', title: 'X', series_position: 1 })).toEqual([]);
	});
});

describe('canonStrip', () => {
	const sized = (slug: string, series_position: number, word_count: number | null, chapter_count = 1) => ({
		slug,
		series_position,
		word_count,
		chapter_count
	});

	it('lays out all 66 books in canonical order, under both testaments, whatever is present', () => {
		const strip = canonStrip([book('john', 43)]);
		expect(strip.map((t) => t.testament)).toEqual(['old', 'new']);
		const slots = strip.flatMap((t) => t.divisions.flatMap((d) => d.slots));
		expect(slots.map((s) => s.position)).toEqual(Array.from({ length: 66 }, (_, i) => i + 1));
		expect(strip.flatMap((t) => t.divisions.map((d) => d.division.id))).toEqual(
			BIBLE_DIVISIONS.map((d) => d.id)
		);
		// Short canon names, not the editions' long titles.
		expect(slots[18].name).toBe('Psalms');
		expect(slots[42]).toMatchObject({ name: 'John', book: { slug: 'john' } });
		expect(slots[45].name).toBe('1 Corinthians');
		expect(slots.filter((s) => s.book)).toHaveLength(1);
	});

	it('leaves an absent book as an empty slot with no weight', () => {
		const slots = canonStrip([]).flatMap((t) => t.divisions.flatMap((d) => d.slots));
		expect(slots).toHaveLength(66);
		expect(slots.every((s) => s.book === null && s.weight === 0)).toBe(true);
	});

	it('weighs a spine by the square root of its words beside the longest book', () => {
		const slots = canonStrip([
			sized('psalms', 19, 40000),
			sized('obadiah', 31, 10000),
			sized('jude', 65, null, 2) // no count: chapters stand in
		]).flatMap((t) => t.divisions.flatMap((d) => d.slots));
		expect(slots[18].weight).toBe(1);
		expect(slots[30].weight).toBe(0.5);
		expect(slots[64].weight).toBe(Math.round(Math.sqrt(1000 / 40000) * 100) / 100);
	});

	it('skips books with no place in the canon and keeps the first of a doubled one', () => {
		const slots = canonStrip([book('x', null), book('y', 99), book('a', 1), book('b', 1)]).flatMap(
			(t) => t.divisions.flatMap((d) => d.slots)
		);
		expect(slots.filter((s) => s.book).map((s) => s.book!.slug)).toEqual(['a']);
	});
});

describe('splitBible', () => {
	const inSeries = (slug: string, series: string | null) => ({ slug, series: series ? { slug: series } : null });

	it("tells the Bible's books by their series", () => {
		expect(isBibleBook(inSeries('genesis', 'the-bible'))).toBe(true);
		expect(isBibleBook(inSeries('rooted-1', 'rooted'))).toBe(false);
		expect(isBibleBook({})).toBe(false);
	});

	it('splits a shelf into the classics and the Bible, keeping each in order', () => {
		const shelf = [
			inSeries('confessions', null),
			inSeries('genesis', 'the-bible'),
			inSeries('rooted-1', 'rooted'),
			inSeries('psalms', 'the-bible')
		];
		const { classics, bible } = splitBible(shelf);
		expect(classics.map((b) => b.slug)).toEqual(['confessions', 'rooted-1']);
		expect(bible.map((b) => b.slug)).toEqual(['genesis', 'psalms']);
	});
});

describe('passageHref', () => {
	const at = { slug: 'gospel-of-john', order: 4 };
	it('opens a verse at its anchor, a range at its first verse', () => {
		expect(passageHref({ reference: 'John 3:16', verses: [{ number: 16 }], bible_chapter: at })).toBe(
			'/books/gospel-of-john/4#v16'
		);
		expect(
			passageHref({ reference: 'Romans 8:28-30', verses: [{ number: 28 }, { number: 29 }], bible_chapter: { slug: 'romans', order: 9 } })
		).toBe('/books/romans/9#v28');
	});
	it('opens a whole chapter at its top', () => {
		expect(
			passageHref({ reference: 'Psalms 23:1-6', verses: [{ number: 1 }], bible_chapter: { slug: 'psalms', order: 24 } })
		).toBe('/books/psalms/24');
		expect(passageHref({ reference: 'John 3', verses: [{ number: 1 }], bible_chapter: at })).toBe(
			'/books/gospel-of-john/4'
		);
	});
	it('opens a bare book at its page, a numbered book too', () => {
		expect(passageHref({ reference: 'John', verses: [{ number: 1 }], bible_chapter: { slug: 'gospel-of-john', order: 2 } })).toBe(
			'/books/gospel-of-john'
		);
		expect(
			passageHref({ reference: '1 Corinthians', verses: [{ number: 1 }], bible_chapter: { slug: '1-corinthians', order: 2 } })
		).toBe('/books/1-corinthians');
	});
	it('is null where the library prints none of it', () => {
		expect(passageHref({ reference: 'Tobit 1:1', verses: [{ number: 1 }], bible_chapter: null })).toBeNull();
		expect(passageHref({ reference: 'John 3:16', verses: [{ number: 16 }] })).toBeNull();
	});
});

describe('bibleStarts', () => {
	it('keeps the curated order and drops a book the series lacks', () => {
		const books = ['romans', 'genesis', 'gospel-of-mark'].map((slug) => ({ slug }));
		expect(bibleStarts(books).map((s) => s.book.slug)).toEqual(['gospel-of-mark', 'genesis', 'romans']);
	});
	it('names five books, each with a reason', () => {
		expect(BIBLE_STARTS).toHaveLength(5);
		for (const s of BIBLE_STARTS) expect(s.why.length).toBeGreaterThan(20);
	});
});

describe('bibleChapterCount', () => {
	it('counts the Bible chapters, not the introduction and conclusion', () => {
		expect(bibleChapterCount([{ chapter_count: 30 }, { chapter_count: 6 }, {}])).toBe(28 + 4);
	});
});

describe('mayBePassage', () => {
	it('asks the resolver for a chapter or a book named alone', () => {
		for (const q of ['John 3:16', 'Ps 23', 'Romans', ' 1 john ', 'Psalm', 'Song of Solomon', 'Rom.'])
			expect(mayBePassage(q), q).toBe(true);
	});
	it('sends any other word to search', () => {
		for (const q of ['grace', 'John Bunyan', 'prayer']) expect(mayBePassage(q), q).toBe(false);
	});
});
