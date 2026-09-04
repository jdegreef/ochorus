import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { saveProgress, saveScrollAnchor, getProgressRecord } from './progress';

// The account mirror is a no-op in these unit tests — we only assert the local
// cache the reader resumes from.
vi.mock('./readingSync', () => ({
	readingSync: { pushProgress: () => {}, pushActivity: () => {} }
}));

beforeEach(() => localStorage.clear());

describe('bookmark deep-link resume point (review bug #16)', () => {
	it('records the jumped-to paragraph when the anchor is seeded first', () => {
		// The reader effect now seeds the anchor for ?p=N before saveProgress.
		saveScrollAnchor('humility', 3, 42);
		saveProgress('humility', 3, 'en');
		expect(getProgressRecord('humility')).toMatchObject({ order: 3, paragraph_index: 42 });
	});

	it('reproduces the old loss when no anchor is seeded (paragraph 0)', () => {
		// Arriving on a fresh chapter with no anchor — the pre-fix behaviour.
		saveProgress('humility', 3, 'en');
		expect(getProgressRecord('humility')?.paragraph_index).toBe(0);
	});

	it('keeps the anchor position for the current chapter across a re-save', () => {
		saveScrollAnchor('humility', 3, 42);
		saveProgress('humility', 3, 'en'); // records 42
		saveProgress('humility', 3, 'en'); // a second open must not clobber it
		expect(getProgressRecord('humility')?.paragraph_index).toBe(42);
	});
});

describe('`at` means when the position last changed', () => {
	beforeEach(() => {
		localStorage.clear();
		vi.useFakeTimers();
	});
	afterEach(() => vi.useRealTimers());

	it('a bare re-open of the same spot leaves the record untouched', () => {
		vi.setSystemTime(1_000_000);
		saveProgress('humility', 3, 'en');
		saveScrollAnchor('humility', 3, 12);
		const before = getProgressRecord('humility');
		expect(before).toMatchObject({ order: 3, paragraph_index: 12, at: 1_000_000 });

		vi.setSystemTime(2_000_000);
		saveProgress('humility', 3, 'en'); // opened again, not moved
		saveScrollAnchor('humility', 3, 12); // the restore lands where it was
		expect(getProgressRecord('humility')).toEqual(before);
	});

	it('moving on re-stamps it', () => {
		vi.setSystemTime(1_000_000);
		saveProgress('humility', 3, 'en');
		vi.setSystemTime(2_000_000);
		saveScrollAnchor('humility', 3, 14);
		expect(getProgressRecord('humility')?.at).toBe(2_000_000);
		vi.setSystemTime(3_000_000);
		saveProgress('humility', 4, 'en');
		expect(getProgressRecord('humility')).toMatchObject({ order: 4, at: 3_000_000 });
	});
});
