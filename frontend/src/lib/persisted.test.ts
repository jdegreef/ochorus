import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { readJSON, writeJSON } from './persisted';
import { storageHealth } from './storageHealth.svelte';

beforeEach(() => {
	localStorage.clear();
	storageHealth.acknowledge();
});
afterEach(() => vi.restoreAllMocks());

describe('readJSON', () => {
	it('returns the fallback when the key is absent', () => {
		expect(readJSON('missing', { a: 1 })).toEqual({ a: 1 });
	});

	it('returns the fallback when the stored value is corrupt', () => {
		localStorage.setItem('bad', '{not json');
		expect(readJSON('bad', [])).toEqual([]);
	});

	it('parses a stored JSON value', () => {
		localStorage.setItem('good', JSON.stringify({ x: [1, 2] }));
		expect(readJSON('good', null)).toEqual({ x: [1, 2] });
	});
});

describe('writeJSON', () => {
	it('round-trips a value through localStorage', () => {
		expect(writeJSON('k', { hello: 'world', n: 3 })).toBe(true);
		expect(readJSON('k', null)).toEqual({ hello: 'world', n: 3 });
		expect(storageHealth.writeFailed).toBe(false);
	});

	it('flags storageHealth and returns false when the write throws (quota/private mode)', () => {
		vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
			throw new DOMException('QuotaExceededError');
		});
		expect(writeJSON('k', { big: 'x' })).toBe(false);
		// A failed write must warn rather than lose the data silently.
		expect(storageHealth.writeFailed).toBe(true);
	});
});
