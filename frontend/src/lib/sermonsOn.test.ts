import { describe, expect, it } from 'vitest';
import type { SermonSummary } from '$lib/library-public';
import {
	SERMONS_ON_FLOOR,
	bibleBookSlug,
	refChapter,
	sermonsOnBooks,
	sermonsOnGroups,
	sermonsOnHref,
	sermonsOnPath,
	sermonsOnPosition
} from './sermonsOn';

const sermon = (slug: string, ref: string, order: number | null): SermonSummary =>
	({ slug, title: slug, scripture_ref: ref, scripture_book_order: order }) as SermonSummary;

describe('sermonsOn slugs', () => {
	it('names a book as a searcher types it, and reads the name back', () => {
		expect(sermonsOnPath(1)).toBe('/sermons/on/genesis/');
		expect(sermonsOnPath(22)).toBe('/sermons/on/song-of-songs/');
		expect(sermonsOnPath(46)).toBe('/sermons/on/1-corinthians/');
		expect(sermonsOnPath(43)).toBe('/sermons/on/john/');
		for (let p = 1; p <= 66; p++)
			expect(sermonsOnPosition(sermonsOnPath(p)!.split('/')[3])).toBe(p);
		expect(sermonsOnPosition('gospel-of-john')).toBeNull();
		expect(sermonsOnPath(67)).toBeNull();
	});

	it('finds the library’s own slug for the book’s text', () => {
		expect(bibleBookSlug(43)).toBe('gospel-of-john');
		expect(bibleBookSlug(1)).toBe('genesis');
		expect(bibleBookSlug(66)).toBe('revelation');
	});
});

describe('sermonsOnBooks / sermonsOnHref', () => {
	it('gives a page only to a book at the floor', () => {
		const rows = [
			...Array.from({ length: SERMONS_ON_FLOOR }, (_, i) => sermon(`j${i}`, 'John 3:16', 43)),
			sermon('g1', 'Genesis 1:1', 1),
			sermon('x', '', null)
		];
		expect(sermonsOnBooks(rows)).toEqual([43]);
		expect(sermonsOnHref(43, SERMONS_ON_FLOOR)).toBe('/sermons/on/john/');
		expect(sermonsOnHref(1, SERMONS_ON_FLOOR - 1)).toBeNull();
		expect(sermonsOnHref(null, 99)).toBeNull();
	});
});

describe('refChapter', () => {
	it('reads the chapter and first verse after the book name', () => {
		expect(refChapter('John 3:16')).toEqual([3, 16]);
		expect(refChapter('Psalm 23')).toEqual([23, 0]);
		expect(refChapter('1 Corinthians 9:26-27')).toEqual([9, 26]);
		expect(refChapter('1 John 5:4-5')).toEqual([5, 4]);
		expect(refChapter('Song of Songs 2:4')).toEqual([2, 4]);
		expect(refChapter('Philemon')).toBeNull();
	});
});

describe('sermonsOnGroups', () => {
	it('groups the book’s sermons by chapter in Bible order, the chapterless last', () => {
		const groups = sermonsOnGroups(
			[
				sermon('b', 'John 14:27', 43),
				sermon('whole', 'John', 43),
				sermon('a', 'John 3:16', 43),
				sermon('c', 'John 3:3', 43),
				sermon('other', 'Romans 8:28', 45)
			],
			43
		);
		expect(groups.map((g) => [g.chapter, g.sermons.map((s) => s.slug)])).toEqual([
			[3, ['c', 'a']],
			[14, ['b']],
			[null, ['whole']]
		]);
	});
});
