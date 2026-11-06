import { describe, expect, it } from 'vitest';
import { firstSentence } from './firstSentence';

describe('firstSentence', () => {
	it('takes the opening sentence', () => {
		expect(firstSentence('Andrew Murray Jr., born in 1828, wrote on prayer. He founded schools.')).toBe(
			'Andrew Murray Jr., born in 1828, wrote on prayer.'
		);
	});

	it('does not stop at initials, a circa or a title', () => {
		expect(firstSentence('C. S. Lewis (1898–1963) was a scholar. More.')).toBe(
			'C. S. Lewis (1898–1963) was a scholar.'
		);
		expect(firstSentence('John Foxe (c. 1516–1587) was a historian. More.')).toBe(
			'John Foxe (c. 1516–1587) was a historian.'
		);
		expect(firstSentence('Dr. Joe E. Church was a doctor. More.')).toBe('Dr. Joe E. Church was a doctor.');
		expect(firstSentence('أ. و. توزر راعٍ أمريكي. ثم')).toBe('أ. و. توزر راعٍ أمريكي.');
	});

	it('ends on the danda and the Arabic question mark', () => {
		expect(firstSentence('डॉ. जो ई. चर्च एक डॉक्टर था। सितंबर')).toBe('डॉ. जो ई. चर्च एक डॉक्टर था।');
	});

	it('holds a long sentence to the budget on a word boundary', () => {
		const out = firstSentence(`${'word '.repeat(80)}end.`, 100);
		expect(out.length).toBeLessThanOrEqual(101);
		expect(out.endsWith('…')).toBe(true);
	});

	it('returns empty for no text', () => {
		expect(firstSentence('')).toBe('');
	});
});
