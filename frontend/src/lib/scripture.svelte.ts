import { browser } from '$app/environment';
import { clampPopoverLeft } from './reading';
import { apiFetch, ApiError } from './api';

/**
 * Tap-a-reference: verse text for a Bible reference in the reading text.
 *
 * References are wrapped server-side in `<a class="scripture-ref" data-ref="…">`;
 * tapping one opens this popover, which fetches the verse text (public-domain
 * American Standard Version) from the Ochorus API. Missing/offline degrades to a
 * gentle "couldn't load" state — the reader never breaks. Cached per session.
 */

export interface ScriptureResult {
	reference: string;
	verses: { number: number; text: string }[];
	version: string;
}

const cache = new Map<string, ScriptureResult | 'none'>();

class Scripture {
	open = $state(false);
	loading = $state(false);
	ref = $state('');
	result = $state<ScriptureResult | null>(null);
	notFound = $state(false);
	top = $state(0);
	left = $state(0);
	#token = 0;

	async show(ref: string, top: number, left: number) {
		if (!browser || !ref) return;
		this.ref = ref;
		this.top = top;
		// 22rem is .scripture-pop's width; a reference near either margin used to
		// render half off-screen.
		this.left = clampPopoverLeft(left, 22 * 16);
		this.open = true;
		this.notFound = false;
		const token = ++this.#token;

		const cached = cache.get(ref);
		if (cached !== undefined) {
			this.loading = false;
			this.result = cached === 'none' ? null : cached;
			this.notFound = cached === 'none';
			return;
		}

		this.loading = true;
		this.result = null;
		try {
			const data = await apiFetch<ScriptureResult>(
				`/api/library/scripture/?ref=${encodeURIComponent(ref)}`
			);
			if (token !== this.#token) return;
			this.result = data;
			cache.set(ref, data);
		} catch (e) {
			if (token !== this.#token) return;
			this.result = null;
			this.notFound = true;
			if (e instanceof ApiError && e.status === 404) cache.set(ref, 'none');
		} finally {
			if (token === this.#token) this.loading = false;
		}
	}

	close() {
		this.open = false;
	}
}

export const scripture = new Scripture();
