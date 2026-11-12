import { describe, expect, it } from 'vitest';
import {
	BIBLE_DIVISIONS,
	biblePlans,
	canonStrip,
	divisionKey,
	divisionOf,
	groupBible,
	testamentKey
} from './bible';
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
