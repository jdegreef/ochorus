import { beforeEach, describe, expect, it, vi } from 'vitest';
import { readingSync } from './readingSync';
import { READING_DATA_KEYS, PROGRESS_KEY, MARKS_KEY } from './reading-schema';

beforeEach(() => localStorage.clear());

describe('readingSync.clearOnSignOut', () => {
	it('removes every reading-data key but leaves device preferences alone', () => {
		for (const key of READING_DATA_KEYS) localStorage.setItem(key, '{"some":"data"}');
		localStorage.setItem('ochorus:reader-prefs', '{"scale":1.2}');
		localStorage.setItem('ochorus:lang', 'lg');

		readingSync.clearOnSignOut();

		for (const key of READING_DATA_KEYS) expect(localStorage.getItem(key)).toBeNull();
		// Theme/font/language are device preferences, not identity data.
		expect(localStorage.getItem('ochorus:reader-prefs')).toBe('{"scale":1.2}');
		expect(localStorage.getItem('ochorus:lang')).toBe('lg');
	});

	it('notifies open views that the cache was emptied', () => {
		const onSync = vi.fn();
		window.addEventListener('ochorus:sync', onSync);
		readingSync.clearOnSignOut();
		window.removeEventListener('ochorus:sync', onSync);
		expect(onSync).toHaveBeenCalledTimes(1);
	});

	it('cancels pending debounced pushes so none fire after sign-out', () => {
		vi.useFakeTimers();
		const fetchSpy = vi.spyOn(globalThis, 'fetch');
		try {
			readingSync.setSignedIn(true);
			readingSync.pushProgress('humility', {
				order: 3,
				paragraph_index: 5,
				language: 'en',
				at: Date.now()
			});
			readingSync.clearOnSignOut();
			vi.runAllTimers();
			expect(fetchSpy).not.toHaveBeenCalled();
		} finally {
			fetchSpy.mockRestore();
			vi.useRealTimers();
			readingSync.setSignedIn(false);
		}
	});

	it('leaves the next sign-in with an empty local cache to merge', () => {
		localStorage.setItem(PROGRESS_KEY, '{"humility":{"order":3}}');
		localStorage.setItem(MARKS_KEY, '{"humility:3":{"m":[]}}');
		readingSync.clearOnSignOut();
		// mergeOnSignIn reads these keys directly; after a wipe the previous
		// user's state must not be part of the next account's merge payload.
		expect(localStorage.getItem(PROGRESS_KEY)).toBeNull();
		expect(localStorage.getItem(MARKS_KEY)).toBeNull();
	});
});
