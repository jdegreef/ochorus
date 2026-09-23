import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
	saveProgress,
	saveScrollAnchor,
	getProgressRecord,
	markFinished,
	unmarkFinished,
	isFinished,
	offerFinishUnopened,
	removeWork,
	restoreWork
} from './progress';
import { pendingAt } from './removals';
import { undo } from './undo.svelte';

// The account mirror is a no-op in these unit tests — we only assert the local
// cache the reader resumes from.
vi.mock('./readingSync', () => ({
	readingSync: {
		pushProgress: () => {},
		pushActivity: () => {},
		setFinished: () => {},
		removeProgress: () => {}
	}
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

describe('finishing a work', () => {
	it('marks finished, is idempotent, and reports the flip', () => {
		saveProgress('humility', 3, 'en');
		expect(isFinished('humility')).toBe(false);
		expect(markFinished('humility')).toBe(true); // flipped
		expect(isFinished('humility')).toBe(true);
		expect(getProgressRecord('humility')?.finished_at).toBeTypeOf('number');
		expect(markFinished('humility')).toBe(false); // already finished — no-op
	});

	it('does nothing for a work with no progress record', () => {
		expect(markFinished('never-opened')).toBe(false);
		expect(getProgressRecord('never-opened')).toBeNull();
	});

	it('reopening a finished work and reading on does NOT un-finish it', () => {
		saveProgress('humility', 34, 'en');
		markFinished('humility');
		// Reopen at another chapter and move — position advances, finish stays.
		saveProgress('humility', 2, 'en');
		saveScrollAnchor('humility', 2, 5);
		expect(getProgressRecord('humility')).toMatchObject({ order: 2, paragraph_index: 5 });
		expect(isFinished('humility')).toBe(true);
	});

	it('un-finishing clears the stamp', () => {
		saveProgress('humility', 3, 'en');
		markFinished('humility');
		unmarkFinished('humility');
		expect(isFinished('humility')).toBe(false);
		expect(getProgressRecord('humility')?.finished_at).toBeNull();
	});

	it('namespaces by kind — finishing a sermon leaves a same-slug book alone', () => {
		saveProgress('humility', 3, 'en', 'book');
		saveProgress('humility', 1, 'en', 'sermon');
		markFinished('humility', 'sermon');
		expect(isFinished('humility', 'sermon')).toBe(true);
		expect(isFinished('humility', 'book')).toBe(false);
	});
});

describe('finishing a book never opened here (the Bookshelf "already read")', () => {
	it('shelves it as finished at its last chapter, and Undo removes every trace', () => {
		offerFinishUnopened('humility', 12, 'en');
		expect(getProgressRecord('humility')).toMatchObject({ order: 12, paragraph_index: 0 });
		expect(isFinished('humility')).toBe(true);
		undo.act();
		expect(getProgressRecord('humility')).toBeNull();
	});

	it('defers to the ordinary finish for a book that has a position', () => {
		saveProgress('humility', 3, 'en');
		offerFinishUnopened('humility', 12, 'en');
		expect(getProgressRecord('humility')).toMatchObject({ order: 3 });
		expect(isFinished('humility')).toBe(true);
	});
});

describe('removing a work from the shelf', () => {
	it('drops the position, remembers the removal, and Undo restores it newer', () => {
		saveProgress('humility', 3, 'en');
		markFinished('humility');
		const before = getProgressRecord('humility')!;
		const rec = removeWork('humility');
		expect(getProgressRecord('humility')).toBeNull();
		expect(pendingAt('progress', 'book', 'humility')).toBeTypeOf('number');

		restoreWork('humility', rec!);
		const back = getProgressRecord('humility')!;
		expect(back).toMatchObject({ order: 3, finished_at: before.finished_at });
		expect(back.at).toBeGreaterThanOrEqual(before.at);
		expect(pendingAt('progress', 'book', 'humility')).toBeNull();
	});

	it('is a no-op for a work with no position', () => {
		expect(removeWork('never-opened')).toBeNull();
		expect(pendingAt('progress', 'book', 'never-opened')).toBeNull();
	});
});
