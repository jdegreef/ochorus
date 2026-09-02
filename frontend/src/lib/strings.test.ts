import { describe, it, expect } from 'vitest';
import { initials, unslug } from './strings';

describe('initials', () => {
	it('takes up to two initials, uppercased', () => {
		expect(initials('Andrew Murray')).toBe('AM');
		expect(initials('a b simpson')).toBe('AB'); // only the first two
		expect(initials('Spurgeon')).toBe('S');
	});
	it('ignores the extra spaces a split would otherwise turn into blanks', () => {
		expect(initials('  Hudson   Taylor ')).toBe('HT');
	});
	it('is empty for an empty name', () => {
		expect(initials('')).toBe('');
	});
});

describe('unslug', () => {
	it('humanises a hyphenated slug', () => {
		expect(unslug('gleanings-among-the-sheaves')).toBe('Gleanings Among The Sheaves');
	});
	it('capitalises single-letter words too (the initials case)', () => {
		expect(unslug('j-c-ryle')).toBe('J C Ryle');
	});
});
