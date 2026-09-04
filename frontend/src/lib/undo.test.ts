import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { undo, UNDO_MS } from './undo.svelte';

beforeEach(() => {
	vi.useFakeTimers();
	undo.dismiss();
});
afterEach(() => vi.useRealTimers());

describe('undo store', () => {
	it('holds one offer and restores on act()', () => {
		const restore = vi.fn();
		undo.offer({ restore });
		expect(undo.current).not.toBeNull();
		undo.act();
		expect(restore).toHaveBeenCalledTimes(1);
		expect(undo.current).toBeNull();
	});

	it('lets an offer go after UNDO_MS', () => {
		const restore = vi.fn();
		undo.offer({ restore });
		vi.advanceTimersByTime(UNDO_MS + 1);
		expect(undo.current).toBeNull();
		undo.act(); // nothing to act on
		expect(restore).not.toHaveBeenCalled();
	});

	it('a second offer replaces the first, and the first timer cannot expire the second', () => {
		const first = vi.fn();
		const second = vi.fn();
		undo.offer({ restore: first });
		vi.advanceTimersByTime(UNDO_MS - 100);
		undo.offer({ restore: second });
		vi.advanceTimersByTime(200); // past the FIRST offer's deadline
		expect(undo.current).not.toBeNull(); // second still live
		undo.act();
		expect(second).toHaveBeenCalledTimes(1);
		expect(first).not.toHaveBeenCalled();
	});

	it('dismiss() drops the offer without restoring', () => {
		const restore = vi.fn();
		undo.offer({ restore });
		undo.dismiss();
		expect(undo.current).toBeNull();
		expect(restore).not.toHaveBeenCalled();
	});
});
