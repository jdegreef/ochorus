import { describe, expect, it } from 'vitest';
import {
	chapterKey,
	parseChapterKey,
	workSlugKey,
	parseWorkSlugKey,
	workKey,
	parseWorkKey
} from './reading-schema';

describe('chapterKey', () => {
	it('joins slug and order with a colon', () => {
		expect(chapterKey('the-inner-chamber', 2)).toBe('the-inner-chamber:2');
	});
});

describe('parseChapterKey', () => {
	it('splits a well-formed key', () => {
		expect(parseChapterKey('the-inner-chamber:2')).toEqual({
			slug: 'the-inner-chamber',
			order: 2
		});
	});

	it('splits on the LAST colon so hyphenated slugs survive', () => {
		expect(parseChapterKey('a-b-c:10')).toEqual({ slug: 'a-b-c', order: 10 });
	});

	it('returns null when there is no colon', () => {
		expect(parseChapterKey('no-colon-here')).toBeNull();
	});

	it('returns null when the order is not a number', () => {
		expect(parseChapterKey('slug:notanumber')).toBeNull();
	});

	it('round-trips with chapterKey', () => {
		for (const [slug, order] of [
			['humility', 1],
			['school-of-prayer', 30],
			['the-inner-chamber', 0]
		] as const) {
			expect(parseChapterKey(chapterKey(slug, order))).toEqual({ slug, order });
		}
	});
});

describe('work keys across kinds', () => {
	it('books keep bare keys; sermons and bios are prefixed', () => {
		expect(workSlugKey('book', 'humility')).toBe('humility');
		expect(workSlugKey('sermon', 'himself')).toBe('sermon:himself');
		expect(workSlugKey('bio', 'andrew-murray')).toBe('bio:andrew-murray');
	});

	it('round-trips every kind through parseWorkSlugKey', () => {
		for (const kind of ['book', 'sermon', 'bio'] as const) {
			expect(parseWorkSlugKey(workSlugKey(kind, 'a-b-simpson'))).toEqual({
				kind,
				slug: 'a-b-simpson'
			});
		}
	});

	it('round-trips chapter-scoped work keys for bios', () => {
		const key = workKey('bio', 'c-h-spurgeon', 1);
		expect(parseWorkKey(key)).toEqual({ kind: 'bio', slug: 'c-h-spurgeon', order: 1 });
	});
});
