import { describe, it, expect, vi, afterEach } from 'vitest';
import { flushSync } from 'svelte';
import { mediaFlag } from './mediaFlag.svelte';

describe('mediaFlag', () => {
	afterEach(() => vi.unstubAllGlobals());

	it('is false until hydration, then follows the query and its changes', () => {
		const listeners: (() => void)[] = [];
		const mq = {
			matches: true,
			addEventListener: (_: string, f: () => void) => listeners.push(f),
			removeEventListener: vi.fn()
		};
		vi.stubGlobal('matchMedia', vi.fn(() => mq));

		let flag!: ReturnType<typeof mediaFlag>;
		const cleanup = $effect.root(() => {
			flag = mediaFlag('(max-width: 34rem)');
			// The prerendered answer, before any effect has run.
			expect(flag.matches).toBe(false);
		});
		flushSync();
		expect(flag.matches).toBe(true);

		mq.matches = false;
		listeners.forEach((f) => f());
		expect(flag.matches).toBe(false);

		cleanup();
		expect(mq.removeEventListener).toHaveBeenCalled();
	});
});
