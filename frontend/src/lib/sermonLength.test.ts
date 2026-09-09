import { describe, it, expect } from 'vitest';
import { lengthBucket, LENGTH_BUCKETS } from './sermonLength';

describe('lengthBucket', () => {
	it('is short below 10 minutes', () => {
		expect(lengthBucket(1)).toBe('short');
		expect(lengthBucket(9)).toBe('short');
	});

	it('is mid from 10 through 30 minutes inclusive — the boundaries the labels claim', () => {
		expect(lengthBucket(10)).toBe('mid');
		expect(lengthBucket(24)).toBe('mid');
		expect(lengthBucket(30)).toBe('mid');
	});

	it('is long above 30 minutes', () => {
		expect(lengthBucket(31)).toBe('long');
		expect(lengthBucket(73)).toBe('long');
	});

	it('LENGTH_BUCKETS lists each bucket once, shortest-first', () => {
		expect(LENGTH_BUCKETS).toEqual(['short', 'mid', 'long']);
	});
});
