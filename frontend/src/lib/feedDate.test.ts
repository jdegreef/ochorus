import { describe, expect, it } from 'vitest';
import { FEED_EPOCH, isoOrEpoch } from './feedDate';

describe('isoOrEpoch', () => {
	it('normalises a real timestamp to ISO', () => {
		expect(isoOrEpoch('2026-08-19T10:18:00Z')).toBe('2026-08-19T10:18:00.000Z');
		expect(isoOrEpoch('2026-08-19')).toBe('2026-08-19T00:00:00.000Z');
	});

	it('falls back to the epoch instead of throwing on a missing date', () => {
		// The regression this exists for: `new Date(undefined).toISOString()` throws
		// RangeError, which failed the feed's prerender and so the whole build.
		expect(() => isoOrEpoch(undefined)).not.toThrow();
		expect(isoOrEpoch(undefined)).toBe(FEED_EPOCH);
		expect(isoOrEpoch(null)).toBe(FEED_EPOCH);
		expect(isoOrEpoch('')).toBe(FEED_EPOCH);
	});

	it('falls back to the epoch on an unparseable date', () => {
		expect(isoOrEpoch('not a date')).toBe(FEED_EPOCH);
		expect(isoOrEpoch('2026-13-45')).toBe(FEED_EPOCH);
	});

	it('sorts undated items last, never as the newest entry', () => {
		const dated = isoOrEpoch('2026-08-19T10:18:00Z');
		const undated = isoOrEpoch(undefined);
		expect([undated, dated].sort((a, b) => b.localeCompare(a))[0]).toBe(dated);
	});
});
