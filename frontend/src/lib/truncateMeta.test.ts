import { describe, it, expect } from 'vitest';
import { truncateMeta } from './seo';

describe('truncateMeta', () => {
	it('returns short text unchanged', () => {
		expect(truncateMeta('A short description.', 160)).toBe('A short description.');
	});

	it('collapses whitespace', () => {
		expect(truncateMeta('  many   spaces\n\there ', 160)).toBe('many spaces here');
	});

	it('ends at a sentence boundary when one falls in the back half of the budget', () => {
		// The first sentence ends at index 40; with max 45 that is past the
		// max*0.6 (27) floor, so the cut lands there — a clean, whole sentence.
		const text = 'The humble heart is a happy heart indeed. And it rests in God alone always.';
		expect(truncateMeta(text, 45)).toBe('The humble heart is a happy heart indeed.');
	});

	it('cuts at a word boundary with an ellipsis when there is no late sentence end', () => {
		const text = 'Andrew Murray explores the profound wisdom of humility and self denial';
		const out = truncateMeta(text, 40);
		expect(out.endsWith('…')).toBe(true);
		expect(out.length).toBeLessThanOrEqual(41); // 40 budget + the ellipsis
		expect(out).not.toMatch(/\s…$/); // no dangling space before the ellipsis
		expect(text.startsWith(out.slice(0, -1))).toBe(true); // a real prefix, no split word tail
	});

	it('ignores a sentence end in the front half rather than returning a stub', () => {
		const text = 'One. ' + 'x'.repeat(200);
		// The only '. ' is at index 3, far below max*0.6, so it must fall through
		// to a word/ellipsis cut instead of collapsing to "One."
		expect(truncateMeta(text, 160)).not.toBe('One.');
	});
});
