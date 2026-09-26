import { describe, it, expect } from 'vitest';
import { QUOTE_MAX, quoteOf, resolveMark } from './markAnchor';
import type { Mark } from './reading-schema';

const mark = (p: number, s: number, e: number, q?: string): Mark => ({ id: 'm1', p, s, e, ...(q ? { q } : {}) });

describe('resolveMark', () => {
	const paras = ['In the beginning was the Word.', 'And the Word was with God.'];

	it('keeps a mark whose words are still at its offsets', () => {
		const m = mark(1, 8, 12, 'Word');
		expect(resolveMark(paras, m)).toBe(m);
	});

	it('keeps a mark made before quotes were stored (nothing to check)', () => {
		const m = mark(0, 0, 2);
		expect(resolveMark(paras, m)).toBe(m);
	});

	it('follows its words when a repair shifts them within the block', () => {
		// "In the beginning" gained a leading word; "Word" moved right by 5.
		const fixed = ['Truly in the beginning was the Word.', paras[1]];
		const m = mark(0, 25, 29, 'Word');
		expect(resolveMark(fixed, m)).toMatchObject({ p: 0, s: 31, e: 35 });
	});

	it('follows its words into a neighbouring block when a paragraph was split', () => {
		const split = ['In the beginning', 'was the Word.', paras[1]];
		const m = mark(1, 22, 25, 'God'); // block 1 was "And the Word…"; now block 2
		expect(resolveMark(split, m)).toMatchObject({ p: 2, s: 22, e: 25 });
	});

	it('prefers the occurrence nearest its old offset', () => {
		const text = ['Word one. Word two. Word three.'];
		const m = mark(0, 10, 14, 'Word'); // the middle one; text shifted by 1
		const shifted = [' ' + text[0]];
		expect(resolveMark(shifted, m)).toMatchObject({ s: 11 });
	});

	it('detaches a mark whose words are gone rather than painting other text', () => {
		const rewritten = ['Something else entirely.', 'Nothing here either.'];
		expect(resolveMark(rewritten, mark(1, 8, 12, 'Word'))).toBeNull();
	});

	it('keeps a to-the-end mark to the end', () => {
		const shifted = ['X ' + paras[0], paras[1]];
		expect(resolveMark(shifted, mark(0, 0, -1, 'In the'))).toMatchObject({ s: 2, e: -1 });
	});
});

describe('quoteOf', () => {
	it('caps the stored anchor text', () => {
		const long = 'a'.repeat(QUOTE_MAX + 50);
		expect(quoteOf(long, 0, long.length)).toHaveLength(QUOTE_MAX);
		expect(quoteOf('hello world', 6, -1)).toBe('world');
	});
});
