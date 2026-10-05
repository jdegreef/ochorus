import type { SignupSource } from './signupSource';

/**
 * A short sign-up suggestion shown as a toast after the reader does something
 * an account would keep — saving a book, a third highlight. One slot, like the
 * Undo offer beside it in PwaToasts; auto-dismissed; and each kind at most once
 * per page session (`id`), so it reads as a remark, not a nag.
 *
 * Callers decide WHEN (signed out only, the right moment); this only shows it.
 */
export interface Nudge {
	/** Once-per-session key, e.g. 'save'. */
	id: string;
	/** The sentence; `%n%` in it is replaced by `n`. */
	textKey: string;
	n?: number;
	/** The link's words and where it goes (already localized). */
	linkKey: string;
	href: string;
	source: SignupSource;
}

export const NUDGE_MS = 8000;

class SignupNudge {
	current = $state<Nudge | null>(null);
	#shown = new Set<string>();
	#timer: ReturnType<typeof setTimeout> | undefined;

	/** Show `n` unless its id was already shown this session. */
	offer(n: Nudge, ms = NUDGE_MS): boolean {
		if (this.#shown.has(n.id)) return false;
		this.#shown.add(n.id);
		clearTimeout(this.#timer);
		this.current = n;
		this.#timer = setTimeout(() => this.dismiss(), ms);
		return true;
	}

	dismiss() {
		clearTimeout(this.#timer);
		this.current = null;
	}

	/** Test seam. */
	_reset() {
		this.dismiss();
		this.#shown.clear();
	}
}

export const signupNudge = new SignupNudge();
