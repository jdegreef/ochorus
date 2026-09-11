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

	it('breaks ties in the canonical books → sermons → articles order', () => {
		expect(topicSectionOrder({ books: 5, sermons: 5, articles: 0 })).toEqual(['books', 'sermons']);
		expect(topicSectionOrder({ books: 0, sermons: 3, articles: 3 })).toEqual(['sermons', 'articles']);
	});

	it('is empty when the topic has no content', () => {
		expect(topicSectionOrder({ books: 0, sermons: 0, articles: 0 })).toEqual([]);
	});
});
