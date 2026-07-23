import { beforeEach, describe, expect, it, vi } from 'vitest';
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
