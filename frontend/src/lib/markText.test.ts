import { describe, it, expect } from 'vitest';
import { paragraphs, segText, groupMarks } from './markText';
import type { Mark } from './reading-schema';

const HTML = '<p>The promises of God are precious.</p><p>Happy is he who knows them.</p>';

describe('paragraphs', () => {
	it('splits top-level blocks into their text content', () => {
		expect(paragraphs(HTML)).toEqual([
			'The promises of God are precious.',
			'Happy is he who knows them.'
		]);
	});
});

describe('segText', () => {
	const paras = paragraphs(HTML);
	it('slices the character range within a block', () => {
		expect(segText(paras, { id: 'a', p: 0, s: 4, e: 12 })).toBe('promises');
	});
	it('e === -1 runs to the end of the block', () => {
		expect(segText(paras, { id: 'a', p: 1, s: 11, e: -1 })).toBe('who knows them.');
	});
});

describe('groupMarks', () => {
	const paras = paragraphs(HTML);
	it('joins multi-block segments sharing an id and carries the note/colour', () => {
		const ms: Mark[] = [
			{ id: 'g', p: 0, s: 4, e: 12, color: 'blue' },
			{ id: 'g', p: 1, s: 0, e: 5, note: 'lovely' }
		];
		const [hl] = groupMarks(paras, ms, 'en');
		expect(hl.text).toBe('promises … Happy');
		expect(hl.note).toBe('lovely');
		expect(hl.color).toBe('blue');
		expect(hl.p).toBe(0);
		expect(hl.edition).toBe('en');
	});
	it('defaults the colour when none is set', () => {
		const [hl] = groupMarks(paras, [{ id: 'x', p: 0, s: 0, e: 3 }], 'en');
		expect(hl.color).toBe('gold');
	});
});
