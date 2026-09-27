import { describe, it, expect } from 'vitest';
import { QUOTE_MAX, placeMarks, quoteOf, resolveGroup, resolveMark } from './markAnchor';
import type { Mark } from './reading-schema';

const mark = (p: number, s: number, e: number, q?: string): Mark => ({
	id: 'm1',
	p,
	s,
	e,
	...(q ? { q } : {})
});

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
		const m = mark(1, 13, 25, 'was with God'); // block 1 was "And the Word…"; now block 2
		expect(resolveMark(split, m)).toMatchObject({ p: 2, s: 13, e: 25 });
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

	it('looks for a short anchor only in its own block', () => {
		const repaired = ['Nothing here.', 'But Word is here.'];
		expect(resolveMark(repaired, mark(0, 4, 8, 'Word'))).toBeNull();
	});

	it('keeps a to-the-end mark to the end', () => {
		const shifted = ['X ' + paras[0], paras[1]];
		expect(resolveMark(shifted, mark(0, 0, -1, 'In the'))).toMatchObject({ s: 2, e: -1 });
	});
});

describe('resolveGroup', () => {
	// One selection from the end of block 1, through block 2, to "And so" at the
	// head of block 3 — three segments sharing an id.
	const paras = [
		'Title.',
		'He spoke of grace that is free to all who ask.',
		'Grace is the free favour of God to the undeserving.',
		'And so we rest.'
	];
	const segs: Mark[] = [
		{ id: 'g', p: 1, s: 12, e: 46, q: 'grace that is free to all who ask.' },
		{ id: 'g', p: 2, s: 0, e: 51, q: paras[2] },
		{ id: 'g', p: 3, s: 0, e: 6, q: 'And so' }
	];

	it('leaves a group in place untouched', () => {
		expect(resolveGroup(paras, segs)).toEqual(segs);
	});

	it('carries a short tail along when the run shifts', () => {
		// A block inserted above the run: the tail's "And so" is too short to be
		// searched for alone, but it moves with the rest.
		const shifted = ['Title.', 'A new line.', ...paras.slice(1)];
		expect(resolveGroup(shifted, segs).map((m) => m?.p)).toEqual([2, 3, 4]);
		// Alone, it would stay behind.
		expect(resolveMark(shifted, segs[2])).toBeNull();
	});

	it('does not let a short tail land on other words in its old block', () => {
		// The run moved down one; the tail's OLD block is now the middle
		// paragraph, which has gained an "And so" of its own.
		const shifted = ['Title.', 'x', paras[1], paras[2] + ' And so on.', paras[3]];
		expect(resolveMark(shifted, segs[2])).toMatchObject({ p: 3, s: 52 }); // alone: wrong words
		expect(resolveGroup(shifted, segs)[2]).toMatchObject({ p: 4, s: 0 }); // as a unit: right
	});

	it('follows a split in the first block of the run', () => {
		const split = [
			'Title.',
			'He spoke of',
			'grace that is free to all who ask.',
			...paras.slice(2)
		];
		const out = resolveGroup(split, segs);
		expect(out.map((m) => m && [m.p, m.s, m.e])).toEqual([
			[2, 0, 34],
			[3, 0, 51],
			[4, 0, 6]
		]);
	});

	it('drops only the segment whose words are gone, and guesses no further', () => {
		// The middle paragraph was split: its whole-block anchor is nowhere now.
		// The tail is short, so without the middle to say how far the run grew it
		// is looked for only where the run was — and isn't there.
		const split = [
			'Title.',
			paras[1],
			'Grace is the free favour of God',
			'to the undeserving.',
			paras[3]
		];
		const out = resolveGroup(split, segs);
		expect(out[0]).toMatchObject({ p: 1, s: 12 });
		expect(out[1]).toBeNull();
		expect(out[2]).toBeNull();
	});

	it('never places a segment before the one ahead of it', () => {
		// "And so" also opens block 1 now; the tail must not jump back there.
		const repeated = ['Title.', 'And so. ' + paras[1], paras[2], 'Then. And so we rest.'];
		expect(resolveGroup(repeated, segs)[2]).toMatchObject({ p: 3, s: 6 });
	});

	it('finds a short first segment when a block appears between it and the lead', () => {
		// "He spoke," ends block 1 and opens the selection; the lead (block 2)
		// moves down one, but the short head never moved.
		const two: Mark[] = [
			{ id: 'h', p: 1, s: 10, e: 19, q: 'He spoke,' },
			{ id: 'h', p: 2, s: 0, e: 51, q: paras[2] }
		];
		const base = ['Title.', 'And then, He spoke,', paras[2]];
		const inserted = [base[0], base[1], 'A heading.', base[2]];
		expect(resolveGroup(inserted, two).map((m) => m && [m.p, m.s])).toEqual([
			[1, 10],
			[3, 0]
		]);
	});

	it('placeMarks resolves groups together and drops only what is gone', () => {
		const shifted = ['Title.', 'A new line.', ...paras.slice(1)];
		const other: Mark = { id: 'h', p: 0, s: 0, e: 6, q: 'Title.' };
		const placed = placeMarks(shifted, [...segs, other]);
		expect(placed.map((m) => `${m.id}@${m.p}`).sort()).toEqual(['g@2', 'g@3', 'g@4', 'h@0']);
	});
});

describe('quoteOf', () => {
	it('caps the stored anchor text', () => {
		const long = 'a'.repeat(QUOTE_MAX + 50);
		expect(quoteOf(long, 0, long.length)).toHaveLength(QUOTE_MAX);
		expect(quoteOf('hello world', 6, -1)).toBe('world');
	});
});
