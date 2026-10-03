import { describe, expect, it } from 'vitest';
import { chapterSuffix, sourceProse } from './quoteSource';

describe('sourceProse', () => {
	it('names a book with its chapter', () => {
		expect(sourceProse({ work: 'All of Grace', order: 2 })).toBe('All of Grace, chapter 2');
	});

	it('names a sermon by its title alone', () => {
		expect(sourceProse({ work: 'Compel Them to Come In', order: null })).toBe(
			'Compel Them to Come In'
		);
		expect(chapterSuffix(null)).toBe('');
	});
});
