import { beforeEach, describe, expect, it } from 'vitest';
import { addPending, clearPending, clearSent, pendingAt, pendingRemovals } from './removals';
import { READING_DATA_KEYS, REMOVALS_KEY } from './reading-schema';

beforeEach(() => localStorage.clear());

describe('pending removals', () => {
	it('keeps one per thing, newest removal wins', () => {
		addPending('favorite', 'book', 'humility', 1);
		addPending('favorite', 'book', 'humility', 2);
		addPending('progress', 'sermon', 'the-secret', 3);
		expect(pendingRemovals()).toEqual([
			{ domain: 'favorite', kind: 'book', slug: 'humility', at: 2 },
			{ domain: 'progress', kind: 'sermon', slug: 'the-secret', at: 3 }
		]);
		expect(pendingAt('favorite', 'book', 'humility')).toBe(2);
	});

	it('an older acknowledgement does not clear a newer removal', () => {
		addPending('progress', 'book', 'humility', 5);
		clearPending('progress', 'book', 'humility', 4);
		expect(pendingAt('progress', 'book', 'humility')).toBe(5);
		clearSent([{ domain: 'progress', kind: 'book', slug: 'humility', at: 5 }]);
		expect(pendingRemovals()).toEqual([]);
	});

	it('skips garbage and is wiped with the reader\'s data on sign-out', () => {
		localStorage.setItem(REMOVALS_KEY, JSON.stringify({ 'galaxy:x:y': 1, 'favorite:book:': 2 }));
		expect(pendingRemovals()).toEqual([]);
		expect(READING_DATA_KEYS).toContain(REMOVALS_KEY);
	});
});
