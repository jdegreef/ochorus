import { describe, expect, it } from 'vitest';
import { topicSectionOrder, topicLeadsWithSeries } from './topicSections';

describe('topicSectionOrder', () => {
	// Design review #16: books lead whatever the counts — the tabs put the
	// sermons one tap away, so they no longer race the books for first place.
	it('leads with books even when sermons outnumber them (On Prayer 17/24/17, The Gospel Call 4/25)', () => {
		expect(topicSectionOrder({ books: 17, sermons: 24, articles: 17 })).toEqual([
			'books', 'sermons', 'articles'
		]);
		expect(topicSectionOrder({ books: 4, sermons: 25, articles: 26 })).toEqual([
			'books', 'sermons', 'articles'
		]);
	});

	it('opens on sermons when a topic has no books (Christ & the Cross)', () => {
		expect(topicSectionOrder({ books: 0, sermons: 9, articles: 0 })).toEqual(['sermons']);
		expect(topicSectionOrder({ books: 0, sermons: 3, articles: 3 })).toEqual(['sermons', 'articles']);
	});

	it('is books-only for a books-only topic (the Puritans)', () => {
		expect(topicSectionOrder({ books: 11, sermons: 0, articles: 0 })).toEqual(['books']);
	});

	it('puts articles last however many there are (Enduring Classics 8/0/61)', () => {
		expect(topicSectionOrder({ books: 8, sermons: 0, articles: 61 })).toEqual(['books', 'articles']);
	});

	it('shows articles alone for an articles-only topic', () => {
		expect(topicSectionOrder({ books: 0, sermons: 0, articles: 4 })).toEqual(['articles']);
	});

	it('is empty when the topic has no content', () => {
		expect(topicSectionOrder({ books: 0, sermons: 0, articles: 0 })).toEqual([]);
	});
});

describe('topicLeadsWithSeries', () => {
	const vol = { series: { slug: 'rooted' } };
	const plain = { series: null };

	it('leads when at least half the books are series volumes', () => {
		expect(topicLeadsWithSeries([vol, vol, plain])).toBe(true);
		expect(topicLeadsWithSeries([vol, plain])).toBe(true);
	});

	it('does not lead with a minority of volumes, or with none', () => {
		expect(topicLeadsWithSeries([vol, plain, plain])).toBe(false);
		expect(topicLeadsWithSeries([plain])).toBe(false);
		expect(topicLeadsWithSeries([])).toBe(false);
	});
});
