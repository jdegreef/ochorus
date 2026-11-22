import { describe, expect, it } from 'vitest';
import { pickBookQuote } from './articleExtras';
import type { Quote } from './library-public';

const q = (text: string, work: string, kind: 'chapter' | 'sermon' = 'chapter'): Quote => ({
	slug: text.slice(0, 8),
	text,
	paragraph: 4,
	source: { kind, slug: 'the-life-of-trust', title: 'Ch', work, order: 2, cover_color: '' }
});

describe('pickBookQuote', () => {
	const long = 'x'.repeat(300);
	const good = 'Do not men believe that God means what he appears plainly to have asserted?';
	it('takes the first quote of the right length from the lead book itself', () => {
		const quotes = [q(good, 'Answers to Prayer'), q('Too short.', 'The Life of Trust'), q(long, 'The Life of Trust'), q(good, 'The Life of Trust')];
		expect(pickBookQuote(quotes, 'The Life of Trust')).toEqual({
			text: good,
			href: '/books/the-life-of-trust/2/?p=4'
		});
	});
	it('is null when the book has none, and never takes a sermon', () => {
		expect(pickBookQuote([q(good, 'The Life of Trust', 'sermon')], 'The Life of Trust')).toBeNull();
		expect(pickBookQuote([], 'The Life of Trust')).toBeNull();
	});
});
