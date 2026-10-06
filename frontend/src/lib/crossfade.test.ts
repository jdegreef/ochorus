import { afterEach, describe, expect, it, vi } from 'vitest';
import { crossfade } from './crossfade';

describe('crossfade', () => {
	const doc = document as unknown as { startViewTransition?: unknown };
	const reduce = (on: boolean) => vi.stubGlobal('matchMedia', () => ({ matches: on }));

	afterEach(() => {
		delete doc.startViewTransition;
		vi.unstubAllGlobals();
	});

	it('runs the change inside a view transition where the browser has one', () => {
		reduce(false);
		const start = vi.fn((cb: () => void) => cb());
		doc.startViewTransition = start;
		const change = vi.fn();
		crossfade(change);
		expect(start).toHaveBeenCalledOnce();
		expect(change).toHaveBeenCalledOnce();
	});

	it('just applies the change for a reader who asks for less motion', () => {
		reduce(true);
		const start = vi.fn();
		doc.startViewTransition = start;
		const change = vi.fn();
		crossfade(change);
		expect(start).not.toHaveBeenCalled();
		expect(change).toHaveBeenCalledOnce();
	});

	it('just applies the change where there is no View Transitions API', () => {
		reduce(false);
		const change = vi.fn();
		crossfade(change);
		expect(change).toHaveBeenCalledOnce();
	});
});
