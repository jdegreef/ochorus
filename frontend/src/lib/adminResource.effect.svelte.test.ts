import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { flushSync } from 'svelte';
import { adminResource } from './adminResource.svelte';
import { auth } from './auth.svelte';

// `adminResource` registers an $effect, so these run inside an effect root.
// What they pin is the effect's DEPENDENCY SET — the part a page can't see.
describe('adminResource dependencies', () => {
	// `auth.enabled` is a plain field off the build's Supabase config, and the
	// test build has none — so it must be forced on for the wait-for-auth rule
	// to be under test at all rather than trivially skipped.
	const configured = auth.enabled;
	beforeEach(() => {
		auth.enabled = true;
		auth.initialized = true;
	});
	afterEach(() => {
		auth.enabled = configured;
	});

	it('loads once auth has settled', () => {
		const cleanup = $effect.root(() => {
			const fetcher = vi.fn(() => Promise.resolve({ n: 1 }));
			adminResource(fetcher, 'fallback');
			flushSync();
			expect(fetcher).toHaveBeenCalledTimes(1);
		});
		cleanup();
	});

	it('waits for auth before the first request', () => {
		auth.initialized = false;
		const cleanup = $effect.root(() => {
			const fetcher = vi.fn(() => Promise.resolve({ n: 1 }));
			adminResource(fetcher, 'fallback');
			flushSync();
			// Firing here would 401 by construction and flash "Not authorised" at
			// an admin who is in fact signed in.
			expect(fetcher, 'must not fire before the session is restored').not.toHaveBeenCalled();
			auth.initialized = true;
			flushSync();
			expect(fetcher).toHaveBeenCalledTimes(1);
		});
		cleanup();
	});

	it('re-fetches when the declared key changes', () => {
		const cleanup = $effect.root(() => {
			let slug = $state('a');
			const fetcher = vi.fn(() => Promise.resolve({ n: 1 }));
			adminResource(fetcher, 'fallback', () => slug);
			flushSync();
			expect(fetcher).toHaveBeenCalledTimes(1);
			slug = 'b';
			flushSync();
			expect(fetcher, 'a detail page must follow its route param').toHaveBeenCalledTimes(2);
		});
		cleanup();
	});

	// The leak this helper exists to close. An async fetcher's reads before its
	// first `await` are tracked like any others, so a queue that builds a query
	// from its filter fields would make every one of them a dependency — and
	// fire a duplicate request on each change, since the filter's own handler
	// already calls load(). `untrack` is what keeps the key list honest.
	it('does not depend on state the fetcher happens to read', () => {
		const cleanup = $effect.root(() => {
			let filter = $state('all');
			const fetcher = vi.fn(() => Promise.resolve({ kind: filter }));
			adminResource(fetcher, 'fallback');
			flushSync();
			expect(fetcher).toHaveBeenCalledTimes(1);
			filter = 'books';
			flushSync();
			expect(fetcher, 'a filter the fetcher reads is not a dependency').toHaveBeenCalledTimes(1);
		});
		cleanup();
	});
});
