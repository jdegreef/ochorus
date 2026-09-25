import { describe, expect, it } from 'vitest';
import { topicSectionOrder } from './topicSections';

describe('topicSectionOrder', () => {
	it('leads with sermons when they dominate (The Gospel Call: 4 books, 25 sermons)', () => {
		expect(topicSectionOrder({ books: 4, sermons: 25, articles: 0 })).toEqual(['sermons', 'books']);
	});

	it('is sermons-only when a topic has no books (Christ & the Cross)', () => {
		expect(topicSectionOrder({ books: 0, sermons: 9, articles: 0 })).toEqual(['sermons']);
	});

	it('leads with books for a book-dominated topic, keeping the rest (On Prayer 10/7/7)', () => {
		expect(topicSectionOrder({ books: 10, sermons: 7, articles: 7 })).toEqual([
			'books', 'sermons', 'articles'
		]);
	});

	it('is books-only for a books-only topic (the Puritans)', () => {
		expect(topicSectionOrder({ books: 11, sermons: 0, articles: 0 })).toEqual(['books']);
	});

	it('breaks a books/sermons tie with books first', () => {
		expect(topicSectionOrder({ books: 5, sermons: 5, articles: 0 })).toEqual(['books', 'sermons']);
		expect(topicSectionOrder({ books: 0, sermons: 3, articles: 3 })).toEqual(['sermons', 'articles']);
	});

	it('puts articles last however many there are (On Prayer 10/7/17, Enduring Classics 8/0/61)', () => {
		expect(topicSectionOrder({ books: 10, sermons: 7, articles: 17 })).toEqual([
			'books', 'sermons', 'articles'
		]);
		expect(topicSectionOrder({ books: 8, sermons: 0, articles: 61 })).toEqual(['books', 'articles']);
		expect(topicSectionOrder({ books: 4, sermons: 25, articles: 26 })).toEqual([
			'sermons', 'books', 'articles'
		]);
	});

	it('shows articles alone for an articles-only topic', () => {
		expect(topicSectionOrder({ books: 0, sermons: 0, articles: 4 })).toEqual(['articles']);
	});

	it('is empty when the topic has no content', () => {
		expect(topicSectionOrder({ books: 0, sermons: 0, articles: 0 })).toEqual([]);
	});
});
