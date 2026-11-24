import { describe, expect, it } from 'vitest';
import {
	BIBLE_LOCALES,
	BIBLE_DIVISIONS,
	bibleBrowseRow,
	matchesCanonFilter,
	THIN_SPINE,
	canonReading,
	spineLabel,
	bibleChapterCount,
	biblePlace,
	bibleToContinue,
	bibleContinueRows,
	biblePlans,
	mayBePassage,
	passageHref,
	divisionKey,
	divisionOf,
	groupBible,
	isBibleBook,
	splitBible,
	testamentKey
} from './bible';
import { canonName, chapterLabel } from './bibleNames';
import {
	BIBLE_PATHS,
	BIBLE_STARTS,
	bibleChapters,
	biblePathSteps,
	bibleStarts,
	bibleTopics,
	canonStrip
} from './bibleHub';
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
		expect(canonName(1, 'en')).toBe('Genesis');
		expect(canonName(66, 'en')).toBe('Revelation');
		expect(canonName(66, 'es')).toBe('Apocalipsis');
		expect(chapterLabel(19, 23, 'es')).toBe('Salmo 23');
		expect(chapterLabel(22, 1, 'es')).toBe('Cantares 1');
		expect([canonName(0, 'en'), canonName(67, 'en'), canonName(null, 'en')]).toEqual([null, null, null]);
	});
});

describe('bibleChapters', () => {
	it('numbers the Bible chapters, past the introduction', () => {
		const chs = bibleChapters({ slug: 'ruth', title: 'Ruth', chapter_count: 6, series_position: 8 }, 'en');
		expect(chs.map((c) => c.n)).toEqual([1, 2, 3, 4]);
		expect(chs[0]).toEqual({ n: 1, name: 'Ruth 1', href: bookChapterPath('ruth', 2, false) });
		expect(chs[3].href).toBe(bookChapterPath('ruth', 5, false));
	});

	it('names a chip as the chapter is titled: the canon short name, "Psalm", or the title off the canon', () => {
		const psalms = bibleChapters({ slug: 'psalms', title: 'The Psalms', chapter_count: 152, series_position: 19 }, 'en');
		expect(psalms[22].name).toBe('Psalm 23');
		expect(bibleChapters({ slug: 'x', title: 'Stray', chapter_count: 3, series_position: null }, 'en')[0].name).toBe(
			'Stray 1'
		);
	});

	it('is empty for a book with no Bible chapters', () => {
		expect(bibleChapters({ slug: 'x', title: 'X', chapter_count: 2, series_position: 1 }, 'en')).toEqual([]);
		expect(bibleChapters({ slug: 'x', title: 'X', series_position: 1 }, 'en')).toEqual([]);
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
		const strip = canonStrip([book('john', 43)], 'en');
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
		const es = canonStrip([], 'es').flatMap((t) => t.divisions.flatMap((d) => d.slots));
		expect([es[0].name, es[30].abbr, es[65].name]).toEqual(['Génesis', 'Abd', 'Apocalipsis']);
		expect(slots.filter((s) => s.book)).toHaveLength(1);
	});

	it('leaves an absent book as an empty slot with no weight', () => {
		const slots = canonStrip([], 'en').flatMap((t) => t.divisions.flatMap((d) => d.slots));
		expect(slots).toHaveLength(66);
		expect(slots.every((s) => s.book === null && s.weight === 0)).toBe(true);
	});

	it('weighs a spine by the square root of its words beside the longest book', () => {
		const slots = canonStrip([
			sized('psalms', 19, 40000),
			sized('obadiah', 31, 10000),
			sized('jude', 65, null, 2) // no count: chapters stand in
		], 'en').flatMap((t) => t.divisions.flatMap((d) => d.slots));
		expect(slots[18].weight).toBe(1);
		expect(slots[30].weight).toBe(0.5);
		expect(slots[64].weight).toBe(Math.round(Math.sqrt(1000 / 40000) * 100) / 100);
	});

	it('skips books with no place in the canon and keeps the first of a doubled one', () => {
		const slots = canonStrip([book('x', null), book('y', 99), book('a', 1), book('b', 1)], 'en').flatMap(
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
			'/books/gospel-of-john/3#v16'
		);
		expect(
			passageHref({ reference: 'Romans 8:28-30', verses: [{ number: 28 }, { number: 29 }], bible_chapter: { slug: 'romans', order: 9 } })
		).toBe('/books/romans/8#v28');
	});
	it('opens a whole chapter at its top', () => {
		expect(
			passageHref({ reference: 'Psalms 23:1-6', verses: [{ number: 1 }], bible_chapter: { slug: 'psalms', order: 24 } })
		).toBe('/books/psalms/23');
		expect(passageHref({ reference: 'John 3', verses: [{ number: 1 }], bible_chapter: at })).toBe(
			'/books/gospel-of-john/3'
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
		expect(bibleStarts(books, 'en').map((s) => s.book.slug)).toEqual(['gospel-of-mark', 'genesis', 'romans']);
	});
	it('names five books, each with a reason', () => {
		expect(BIBLE_STARTS).toHaveLength(5);
		for (const s of BIBLE_STARTS)
			for (const l of BIBLE_LOCALES) expect(s.why[l].length, `${s.slug} ${l}`).toBeGreaterThan(20);
		expect(bibleStarts([{ slug: 'psalms' }], 'es')[0].why).toMatch(/^El libro de oración/);
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

describe('biblePlace', () => {
	// Ruth: an introduction, four chapters, a conclusion (orders 1-6).
	const ruth = { chapter_count: 6 };
	const rec = (order: number, furthest?: number, finished_at: number | null = null) => ({
		order,
		furthest,
		finished_at
	});

	it('reads nothing for no record, or a place outside the edition', () => {
		expect(biblePlace(ruth, null)).toBeNull();
		expect(biblePlace(ruth, rec(9))).toBeNull();
	});

	it('puts the chapters before the furthest reached behind the reader', () => {
		// On Ruth 3 (order 4), having reached it: Ruth 1-2 behind.
		expect(biblePlace(ruth, rec(4))).toEqual({ behind: 2, current: 3, finished: false });
		// Back in Ruth 1 after reaching Ruth 4: Continue goes to Ruth 1, 1-3 behind.
		expect(biblePlace(ruth, rec(2, 5))).toEqual({ behind: 3, current: 1, finished: false });
	});

	it('has no current chapter at the introduction or the conclusion', () => {
		expect(biblePlace(ruth, rec(1))).toEqual({ behind: 0, current: null, finished: false });
		expect(biblePlace(ruth, rec(6))).toEqual({ behind: 4, current: null, finished: false });
	});

	it('marks every chapter behind a finished reader', () => {
		expect(biblePlace(ruth, rec(3, 3, 1))).toEqual({ behind: 4, current: null, finished: true });
	});

	it('reads a book started again after finishing as in progress', () => {
		const reread = { order: 3, furthest: 3, finished_at: 1, restarted_at: 5 };
		expect(biblePlace(ruth, reread)).toEqual({ behind: 1, current: 2, finished: false });
		// ...and finished again once the reread is.
		expect(biblePlace(ruth, { ...reread, last_finished_at: 9 })?.finished).toBe(true);
	});
});

describe('bibleToContinue', () => {
	const books = [
		{ slug: 'ruth', chapter_count: 6 },
		{ slug: 'jonah', chapter_count: 6 },
		{ slug: 'mark', chapter_count: 18 }
	];
	const at = (slug: string, order: number, when: number, extra: object = {}) => ({
		slug,
		kind: 'book',
		order,
		furthest: order,
		finished_at: null,
		at: when,
		...extra
	});

	it('lists the books partway through, newest first, linking the chapter to read', () => {
		const rows = bibleToContinue(books, [at('ruth', 3, 1), at('mark', 8, 5)]);
		expect(rows.map((r) => [r.book.slug, r.chapter, r.order, r.count])).toEqual([
			['mark', 7, 8, 16],
			['ruth', 2, 3, 4]
		]);
		expect(rows[0].record.slug).toBe('mark');
	});

	it('skips finished books, introductions, other works and books off the shelf', () => {
		const rows = bibleToContinue(books, [
			at('ruth', 3, 1, { finished_at: 9 }),
			at('jonah', 1, 2),
			at('mark', 3, 3, { kind: 'sermon' }),
			at('pilgrims-progress', 3, 4)
		]);
		expect(rows).toEqual([]);
	});

	it('keeps at most three', () => {
		const many = [...books, { slug: 'joel', chapter_count: 5 }];
		const recs = many.map((b, i) => at(b.slug, 2, i));
		expect(bibleToContinue(many, recs).map((r) => r.book.slug)).toEqual(['joel', 'mark', 'jonah']);
	});
});

describe('bibleContinueRows', () => {
	const plan = (slug: string, ...covers: string[]) => ({ slug, covers: covers.map((c) => ({ slug: c })) });
	const row = (slug: string) => ({ book: { slug } });

	it('puts plans first and drops the book a one-book plan already reads', () => {
		const out = bibleContinueRows([plan('john-in-21-days', 'gospel-of-john')], [row('gospel-of-john'), row('ruth')]);
		expect(out.plans.map((p) => p.slug)).toEqual(['john-in-21-days']);
		expect(out.books.map((r) => r.book.slug)).toEqual(['ruth']);
	});

	it('keeps a book a many-book plan also reads', () => {
		const out = bibleContinueRows([plan('bible-in-a-year', 'genesis', 'exodus')], [row('genesis')]);
		expect(out.books.map((r) => r.book.slug)).toEqual(['genesis']);
	});

	it('shows at most `max` rows in all', () => {
		const out = bibleContinueRows([plan('a', 'x'), plan('b', 'y')], [row('c'), row('d')], 3);
		expect([out.plans.length, out.books.length]).toEqual([2, 1]);
		expect(bibleContinueRows([plan('a'), plan('b'), plan('c'), plan('d')], [row('e')]).plans).toHaveLength(3);
	});
});

describe('canon strip: names, height, reading', () => {
	const sized = (slug: string, pos: number, word_count: number, chapter_count: number) => ({
		slug,
		series_position: pos,
		word_count,
		chapter_count
	});
	const slots = canonStrip([
		sized('psalms', 19, 50000, 152),
		sized('obadiah', 31, 2500, 3),
		sized('romans', 45, 15000, 18)
	], 'en').flatMap((t) => t.divisions.flatMap((d) => d.slots));
	const at = (pos: number) => slots.find((s) => s.position === pos)!;

	it('carries each book its abbreviation, its Bible chapters and its height', () => {
		expect(at(31).abbr).toBe('Obad');
		expect(at(19).chapters).toBe(150);
		expect(at(19).tall).toBe(1);
		expect(at(31).tall).toBe(Math.round((1 / Math.sqrt(150)) * 100) / 100);
		expect(at(1)).toMatchObject({ book: null, chapters: 0, tall: 0 });
	});

	it('labels a thin spine with its abbreviation, a wide one with its name', () => {
		expect(at(31).weight).toBeLessThan(THIN_SPINE);
		expect(spineLabel(at(31))).toBe('Obad');
		expect(spineLabel(at(19))).toBe('Psalms');
		// An absent book has no width to save: its own label is the strip's to choose.
		expect(spineLabel(at(1))).toBe('Genesis');
	});

	it('counts the books finished and under way', () => {
		const places = {
			psalms: { behind: 150, current: null, finished: true },
			romans: { behind: 3, current: 4, finished: false },
			obadiah: null
		} as const;
		const books = [{ slug: 'psalms' }, { slug: 'romans' }, { slug: 'obadiah' }] as const;
		expect(canonReading(books, (b) => places[b.slug])).toEqual({ finished: 1, started: 1, total: 3 });
	});
});

describe('matchesCanonFilter', () => {
	const fresh = null;
	const started = { behind: 2, current: 3, finished: false };
	const done = { behind: 5, current: null, finished: true };
	it('keeps the short books by reading time', () => {
		expect(matchesCanonFilter('short', 'law', 18, fresh)).toBe(true);
		expect(matchesCanonFilter('short', 'law', 20, fresh)).toBe(true);
		expect(matchesCanonFilter('short', 'law', 21, fresh)).toBe(false);
		expect(matchesCanonFilter('short', 'law', null, fresh)).toBe(false);
	});
	it('keeps a division or two', () => {
		expect(matchesCanonFilter('gospels', 'gospels', 90, fresh)).toBe(true);
		expect(matchesCanonFilter('gospels', 'acts', 90, fresh)).toBe(false);
		expect(matchesCanonFilter('poetry', 'wisdom', 90, fresh)).toBe(true);
		expect(matchesCanonFilter('letters', 'paul', 90, fresh)).toBe(true);
		expect(matchesCanonFilter('letters', 'general-letters', 90, fresh)).toBe(true);
		expect(matchesCanonFilter('letters', 'revelation', 90, fresh)).toBe(false);
	});
	it('keeps the books not yet started', () => {
		expect(matchesCanonFilter('unread', 'law', 90, fresh)).toBe(true);
		expect(matchesCanonFilter('unread', 'law', 90, { behind: 0, current: null, finished: false })).toBe(true);
		expect(matchesCanonFilter('unread', 'law', 90, started)).toBe(false);
		expect(matchesCanonFilter('unread', 'law', 90, done)).toBe(false);
	});
});

describe('bibleBrowseRow', () => {
	it('sets the Browse tab\'s Bible row in its own order, leaving out what the language lacks', () => {
		const shelf = ['romans', 'gospel-of-john', 'obadiah', 'genesis', 'psalms'].map((slug) => ({ slug }));
		expect(bibleBrowseRow(shelf).map((b) => b.slug)).toEqual(['genesis', 'psalms', 'gospel-of-john', 'romans']);
		expect(bibleBrowseRow([])).toEqual([]);
	});
});

describe('bibleTopics', () => {
	it('keeps the subjects whose shelf exists, in their own order', () => {
		const out = bibleTopics([{ slug: 'holy-spirit' }, { slug: 'prayer' }, { slug: 'the-puritans' }]);
		expect(out.map((t) => t.slug)).toEqual(['prayer', 'holy-spirit']);
		expect(out[0].label).toBe('Prayer');
		expect(bibleTopics([])).toEqual([]);
	});
});

describe('biblePathSteps', () => {
	const W = { en: 'w', es: 'v' };
	const ps = { slug: 'psalms', title: 'The Psalms', series_position: 19, chapter_count: 152 };
	const john = { slug: 'gospel-of-john', title: 'The Gospel of John', series_position: 43, chapter_count: 23 };

	it('opens each step at its chapter, named as the chapter is titled', () => {
		const out = biblePathSteps([{ position: 19, chapter: 23, why: W }], [ps], 'en');
		expect(out).toEqual([
			{ book: ps, title: 'Psalm 23', href: bookChapterPath('psalms', 24, false), why: 'w' }
		]);
	});

	it('opens a whole-book step at the book', () => {
		expect(biblePathSteps([{ position: 43, why: W }], [john], 'en')[0]).toMatchObject({
			title: 'The Gospel of John',
			href: '/books/gospel-of-john'
		});
	});

	it('leaves out a book the library lacks, or a chapter past its end', () => {
		expect(biblePathSteps([{ position: 1, chapter: 1, why: W }], [ps], 'en')).toEqual([]);
		expect(biblePathSteps([{ position: 43, chapter: 30, why: W }], [john], 'en')).toEqual([]);
	});

	it('names real chapters in every path', () => {
		// Every step is inside its book's chapter range (the canon's own counts).
		const LAST: Record<number, number> = { 1: 50, 19: 150, 20: 31, 23: 66, 40: 28, 41: 16, 42: 24, 43: 21, 45: 16, 50: 4, 51: 4, 52: 5, 59: 5, 66: 22 };
		for (const p of BIBLE_PATHS)
			for (const s of p.steps) expect(s.chapter ?? 1).toBeLessThanOrEqual(LAST[s.position] ?? 0);
		expect(new Set(BIBLE_PATHS.map((p) => p.id)).size).toBe(BIBLE_PATHS.length);
		for (const p of BIBLE_PATHS)
			for (const l of BIBLE_LOCALES) {
				expect(p.label[l] && p.lede[l], `${p.id} ${l}`).toBeTruthy();
				for (const st of p.steps) expect(st.why[l].length, `${p.id} ${l}`).toBeGreaterThan(20);
			}
	});
});

describe('Spanish quotations on the hub', () => {
	it('quote the Open Word Bible (owb-es-b) word for word', async () => {
		const { readFileSync } = await import('node:fs');
		const { gunzipSync } = await import('node:zlib');
		const { resolve } = await import('node:path');
		const owb = JSON.parse(
			gunzipSync(
				readFileSync(resolve(__dirname, '../../../backend/library/data/bible/owb-es-b.json.gz'))
			).toString('utf8')
		) as { verses: Record<string, string> };
		const text = Object.values(owb.verses).join(' ');
		const reasons = [
			...BIBLE_STARTS.map((s) => s.why.es),
			...BIBLE_PATHS.flatMap((p) => p.steps.map((s) => s.why.es))
		];
		const quoted = reasons.flatMap((r) => [...r.matchAll(/«([^»]+)»/g)].map((m) => m[1]));
		expect(quoted.length).toBeGreaterThan(0);
		for (const q of quoted) expect(text, q).toContain(q);
	});
});
