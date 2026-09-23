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

/**
 * The verse text for a reference, or null when there is none (cached, like a
 * hit) or it couldn't be fetched (offline — not cached, so it is retried).
 * Shared by the tap-a-reference popover and the Notebook's daily prayer.
 */
export async function lookupScripture(ref: string): Promise<ScriptureResult | null> {
	const cached = cache.get(ref);
	if (cached !== undefined) return cached === 'none' ? null : cached;
	try {
		const data = await apiFetch<ScriptureResult>(
			`/api/library/scripture/?ref=${encodeURIComponent(ref)}`
		);
		cache.set(ref, data);
		return data;
	} catch (e) {
		if (e instanceof ApiError && e.status === 404) cache.set(ref, 'none');
		return null;
	}
}

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

		this.loading = !cache.has(ref);
		this.result = null;
		const data = await lookupScripture(ref);
		if (token !== this.#token) return;
		this.result = data;
		this.notFound = data === null;
		this.loading = false;
	}

	close() {
		this.open = false;
	}
}

export const scripture = new Scripture();
