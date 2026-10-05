import { describe, expect, it } from 'vitest';
import { midBook, type MidBookWelcome } from './midBook.svelte';

const w = (slug: string): MidBookWelcome => ({
	slug,
	bookTitle: 'All of Grace',
	author: 'C. H. Spurgeon',
	order: 14,
	firstHref: `/books/${slug}/1`,
	bookHref: `/books/${slug}`
});

describe('midBook', () => {
	it('shows, clears quietly, and can show again', () => {
		midBook.show(w('a'));
		expect(midBook.current?.slug).toBe('a');
		midBook.clear();
		expect(midBook.current).toBeNull();
		midBook.show(w('a'));
		expect(midBook.current?.slug).toBe('a');
		midBook.clear();
	});

	it('a dismissal holds for that book only', () => {
		midBook.show(w('b'));
		midBook.dismiss();
		midBook.show(w('b'));
		expect(midBook.current).toBeNull();
		midBook.show(w('c'));
		expect(midBook.current?.slug).toBe('c');
		midBook.clear();
	});
});

describe('midBook.landing', () => {
	it('is true until the first in-app navigation, then stays false', () => {
		expect(midBook.landing).toBe(true);
		midBook.navigated();
		expect(midBook.landing).toBe(false);
	});
});
