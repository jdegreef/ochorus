import { describe, expect, it } from 'vitest';
import { appendPhrase } from './dictation.svelte';

describe('appendPhrase', () => {
	it('opens with a capital and joins phrases with a space', () => {
		expect(appendPhrase('', 'thank you for today')).toBe('Thank you for today');
		expect(appendPhrase('Thank you for today', 'and for rest')).toBe('Thank you for today and for rest');
	});

	it('capitalises after the end of a sentence or a new line', () => {
		expect(appendPhrase('Amen.', 'lord help anna')).toBe('Amen. Lord help anna');
		expect(appendPhrase('Anna — \n', 'peace')).toBe('Anna — \nPeace');
		expect(appendPhrase('Is it you?  ', 'yes')).toBe('Is it you? Yes');
	});

	it('ignores an empty phrase', () => {
		expect(appendPhrase('Kept.', '   ')).toBe('Kept.');
	});
});
