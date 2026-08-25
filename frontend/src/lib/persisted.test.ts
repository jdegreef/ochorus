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

/**
 * Cross-tab sync: another tab's write must reach this tab's stores.
 *
 * Every reading store is a read-modify-write over a whole JSON blob, so without
 * this two tabs open on Ochorus drift apart and the last full-blob write wins —
 * a highlight made in one tab destroyed when the other saves a scroll anchor.
 * `PlansProgress.svelte` even promised this sync existed ("a day marked on
 * another tab…"); it did not.
 *
 * The listener registers at module load, and the import above already did that,
 * so these tests listen for the re-broadcast rather than re-importing.
 */
describe('cross-tab sync', () => {
	let synced = 0;
	const onSync = () => (synced += 1);

	beforeEach(() => {
		synced = 0;
		window.addEventListener('ochorus:sync', onSync);
	});
	afterEach(() => window.removeEventListener('ochorus:sync', onSync));

	/** Fire a `storage` event the way another tab's write would. */
	function otherTabWrote(key: string | null) {
		const event = new Event('storage');
		Object.defineProperty(event, 'key', { value: key, configurable: true });
		window.dispatchEvent(event);
	}

	it('re-broadcasts another tab’s write to one of our keys', () => {
		otherTabWrote('ochorus:marks');
		expect(synced).toBe(1);
	});

	it('covers every reading store, not just one', () => {
		for (const key of [
			'ochorus:progress',
			'ochorus:bookmarks',
			'ochorus:plans',
			'ochorus:favorites',
			'ochorus:activity'
		]) {
			otherTabWrote(key);
		}
		expect(synced).toBe(5);
	});

	it('treats a whole-storage clear as a sync', () => {
		// key === null is another tab signing out; every store must re-read.
		otherTabWrote(null);
		expect(synced).toBe(1);
	});

	it('ignores keys belonging to something else on this origin', () => {
		otherTabWrote('some-other-app:token');
		otherTabWrote('theme-unprefixed');
		expect(synced).toBe(0);
	});
});
