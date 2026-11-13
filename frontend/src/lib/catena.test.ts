import { describe, expect, it } from 'vitest';
import { catenaPassageHref, passageFor, spanId } from './catena';
import type { CatenaPassage } from './library-public';

const passage = (ref: string, p: number): CatenaPassage => ({
	ref,
	reference: `John ${ref}`,
	text: 'In the beginning was the Word.',
	chapter: 2,
	p,
	excerpts: [{ author: 'Augustine', work: 'Tractates on John', text: 'Hear, brethren.' }]
});

describe('catenaPassageHref', () => {
	it('opens the catena chapter at the block that quotes the span', () => {
		expect(catenaPassageHref('catena-on-john', 4, 11)).toBe('/books/catena-on-john/4?p=11');
	});
	it('needs no jump for a block at the top of the chapter', () => {
		expect(catenaPassageHref('catena-on-john', 2, 0)).toBe('/books/catena-on-john/2');
	});
});

describe('passageFor', () => {
	const passages = [passage('3:1–2', 1), passage('3:16', 30)];
	it('finds the passage a chip names', () => {
		expect(passageFor(passages, '3:16')?.p).toBe(30);
	});
	it('is null for a span the served index lacks', () => {
		expect(passageFor(passages, '3:17')).toBeNull();
	});
});

describe('spanId', () => {
	it('makes a span safe for an element id', () => {
		expect(spanId('7:53–8:11')).toBe('7-53-8-11');
	});
});
