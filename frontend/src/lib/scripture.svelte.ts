import { browser } from '$app/environment';
import { clampPopoverLeft } from './reading';
import { apiFetch, ApiError } from './api';

/**
 * Tap-a-reference: verse text for a Bible reference in the reading text.
 *
 * References are wrapped server-side in `<a class="scripture-ref" data-ref="…">`;
 * tapping one opens this popover, which fetches the verse text (the CC0
 * Open Word Bible) from the Ochorus API. Missing/offline degrades to a
 * gentle "couldn't load" state — the reader never breaks. Cached per session.
 */

export interface ScriptureResult {
	reference: string;
	verses: { number: number; text: string }[];
	version: string;
	/** True when only the first verses came back (a whole chapter is cut). */
	truncated?: boolean;
	/** Where the library's own Bible prints the chapter the reference starts
	 *  in — reader chapter `order` of book `slug` — or null when it has no
	 *  edition of that book. English editions only; optional: an API behind
	 *  this build omits it. */
	bible_chapter?: { slug: string; order: number } | null;
}

const cache = new Map<string, ScriptureResult | 'none' | 'omitted'>();

/**
 * True when the API said the reference is a real verse that its Bibles don't
 * print (Matthew 17:21, Acts 8:37: the KJV-era classics quote them, the modern
 * critical text lacks them). Read after `lookupScripture` has answered null.
 */
export const isOmittedVerse = (ref: string) => cache.get(ref) === 'omitted';

/**
 * The verse text for a reference, or null when there is none (cached, like a
 * hit) or it couldn't be fetched (offline — not cached, so it is retried).
 * Shared by the tap-a-reference popover and the Notebook's daily prayer.
 */
export async function lookupScripture(ref: string): Promise<ScriptureResult | null> {
	const cached = cache.get(ref);
	if (cached !== undefined) return typeof cached === 'string' ? null : cached;
	try {
		const data = await apiFetch<ScriptureResult>(
			`/api/library/scripture/?ref=${encodeURIComponent(ref)}`
		);
		cache.set(ref, data);
		return data;
	} catch (e) {
		if (e instanceof ApiError && e.status === 404) {
			const omitted = (e.body as { omitted?: boolean } | null)?.omitted === true;
			cache.set(ref, omitted ? 'omitted' : 'none');
		}
		return null;
	}
}

class Scripture {
	open = $state(false);
	loading = $state(false);
	ref = $state('');
	/** The reference's scripture page, when the server linked it ('' if none). */
	href = $state('');
	result = $state<ScriptureResult | null>(null);
	notFound = $state(false);
	/** Not found because the verse is one the modern text omits — see isOmittedVerse. */
	omitted = $state(false);
	top = $state(0);
	left = $state(0);
	#token = 0;

	async show(ref: string, top: number, left: number, href = '') {
		if (!browser || !ref) return;
		this.ref = ref;
		this.href = href;
		this.top = top;
		// 22rem is .scripture-pop's width; a reference near either margin used to
		// render half off-screen.
		this.left = clampPopoverLeft(left, 22 * 16);
		this.open = true;
		this.notFound = false;
		this.omitted = false;
		const token = ++this.#token;

		this.loading = !cache.has(ref);
		this.result = null;
		const data = await lookupScripture(ref);
		if (token !== this.#token) return;
		this.result = data;
		this.notFound = data === null;
		this.omitted = data === null && isOmittedVerse(ref);
		this.loading = false;
	}

	close() {
		this.open = false;
	}
}

export const scripture = new Scripture();
