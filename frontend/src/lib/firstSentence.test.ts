import { describe, expect, it } from 'vitest';
import { firstSentence } from './firstSentence';

describe('firstSentence', () => {
	it('takes the opening sentence', () => {
		expect(firstSentence('Andrew Murray Jr., born in 1828, wrote on prayer. He founded schools.')).toBe(
			'Andrew Murray Jr., born in 1828, wrote on prayer.'
		);
	});

	it('ends after a digit, a bracket or a closing quote', () => {
		expect(firstSentence('He was born in 1828. He founded schools.')).toBe('He was born in 1828.');
		expect(firstSentence('Dora Yu (1873–1931). A trained doctor.')).toBe('Dora Yu (1873–1931).');
		expect(firstSentence('He wrote “Joy to the World.” Laid aside by illness.')).toBe(
			'He wrote “Joy to the World.”'
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
		expect(firstSentence('डॉ. जो ई. चर्च एक डॉक्टर था। सितंबर')).toBe('डॉ. जो ई. चर्च एक डॉक्टर था।');
	});

	it('ends on the Ethiopic full stop', () => {
		expect(firstSentence('አንድሩ መሬይ ሰባኪ ነበር። ብዙ መጻሕፍት ጻፈ።')).toBe('አንድሩ መሬይ ሰባኪ ነበር።');
	});

	it('cuts a long sentence on a word with an ellipsis, not at an inner stop', () => {
		const long = `He was the founding pastor of St. Thomas’s Church ${'and much more '.repeat(20)}there.`;
		const out = firstSentence(long, 100);
		expect(out.length).toBeLessThanOrEqual(101);
		expect(out.endsWith('…')).toBe(true);
		expect(out).toContain('St. Thomas');
	});

	it('returns empty for no text', () => {
		expect(firstSentence('')).toBe('');
	});
});
