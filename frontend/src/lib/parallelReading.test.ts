import { describe, expect, it } from 'vitest';
import { blockCount, parallelActive, parallelLayout, parallelOffered, rowHeights } from './parallelReading';

describe('parallelLayout — when the two editions may be paired row by row', () => {
	it('pairs paragraphs when both editions have the same block count', () => {
		expect(parallelLayout(12, 12)).toBe('rows');
	});

	it('falls back to free columns when the counts differ, never misaligning', () => {
		expect(parallelLayout(12, 13)).toBe('columns');
		expect(parallelLayout(13, 12)).toBe('columns');
	});

	it('has nothing to pair in an empty chapter', () => {
		expect(parallelLayout(0, 0)).toBe('columns');
	});

	it('counts top-level blocks the way the reader indexes ?p= and marks', () => {
		const original = '<p>One <em>two</em></p><h2>Head</h2><blockquote><p>q</p></blockquote><hr>';
		const modern = '<p>One, two.</p><h2>Head</h2><blockquote><p>q</p><p>r</p></blockquote><hr>';
		// Nested paragraphs don't count: both are 4 blocks, so they pair.
		expect(blockCount(original)).toBe(4);
		expect(parallelLayout(blockCount(original), blockCount(modern))).toBe('rows');
		// A careful pass that split one paragraph in two shifts every row after it.
		expect(parallelLayout(blockCount(original), blockCount(modern + '<p>extra</p>'))).toBe('columns');
	});
});

describe('rowHeights', () => {
	it('gives each row the taller cell of its pair', () => {
		expect(rowHeights([10, 40, 5], [20, 30, 5])).toEqual([20, 40, 5]);
	});
});

describe('parallel gating — which pages offer and lay out side by side', () => {
	const base = { hasModern: true, language: 'en', wide: true };

	it('is offered on both editions of a work with a Modern English edition, on a wide screen', () => {
		expect(parallelOffered(base)).toBe(true);
		expect(parallelOffered({ ...base, language: 'en-modern' })).toBe(true);
	});

	it('is never offered on phones or narrow tablets', () => {
		expect(parallelOffered({ ...base, wide: false })).toBe(false);
	});

	it('is not offered without a Modern English edition, nor on a translation', () => {
		expect(parallelOffered({ ...base, hasModern: false })).toBe(false);
		expect(parallelOffered({ ...base, hasModern: undefined })).toBe(false);
		expect(parallelOffered({ ...base, language: 'es' })).toBe(false);
	});

	it('lays out side by side only on the Original route, with the preference on', () => {
		expect(parallelActive({ ...base, pref: true, edition: null })).toBe(true);
		expect(parallelActive({ ...base, pref: false, edition: null })).toBe(false);
		expect(parallelActive({ ...base, language: 'en-modern', pref: true, edition: 'modern' })).toBe(false);
		expect(parallelActive({ ...base, wide: false, pref: true, edition: null })).toBe(false);
	});
});
