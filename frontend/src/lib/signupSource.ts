import type { Action } from 'svelte/action';
import { readJSON, writeJSON } from './persisted';
import { SIGNUP_VARIANTS } from './signupBand';
import { track } from './analytics';
import { withParam } from './loginHref';

/**
 * Where a sign-up came from — every prompt that asks for an account, not just
 * the home band.
 *
 * A prompt links to /login with `?src=<source>`; the login page records that
 * source here (`noteSignupSource`), and `auth` sends it with the sign-up the
 * same way the band's arm always travelled (Supabase user_metadata for email
 * sign-ups, POST /api/auth/signup-source/ for Google). Django stores it
 * create-only in `UserProfile.signup_variant`, so the admin can count accounts
 * per source exactly, ad blockers or not.
 *
 * Credit goes to the LAST prompt the reader followed, within 24 hours — the
 * one that actually brought them to the form. With none (a direct visit, or an
 * untagged sign-in link), the account has no source; the home band is credited
 * only when its own button was followed, like every other prompt.
 *
 * Views and starts are Plausible custom events (`Signup prompt seen`,
 * `Signup started`, each with a `source` prop): a label only, never a URL or
 * anything personal, and a no-op when Plausible is off. "Seen" means the
 * prompt's button actually scrolled into view (`seenOnView`), so a footer
 * nobody reached doesn't count.
 */

/** Prompts other than the home band. Kept in step with backend
 *  `accounts.models.SIGNUP_VARIANTS`, which holds the band arms AND these. */
export const PROMPT_SOURCES = [
	'bookshelf',
	'notebook',
	'save_toast',
	'highlight_toast',
	'chapter_end',
	'plan_start',
	'article',
	'quote',
	'footer',
	'header',
	'menu',
	'feedback',
	'one_tap'
] as const;

export const SIGNUP_SOURCES = [...SIGNUP_VARIANTS, ...PROMPT_SOURCES] as const;
export type SignupSource = (typeof SIGNUP_SOURCES)[number];

const KEY = 'ochorus:signup_source';
/** How long a followed prompt keeps the credit. */
export const SOURCE_TTL_MS = 24 * 60 * 60 * 1000;

export function isSignupSource(value: unknown): value is SignupSource {
	return typeof value === 'string' && (SIGNUP_SOURCES as readonly string[]).includes(value);
}

/** Record that the reader followed `source` to the sign-up form (last wins). */
export function noteSignupSource(source: SignupSource, now = Date.now()): void {
	writeJSON(KEY, { source, at: now });
}

/**
 * `noteSignupSource`, plus an undo that puts back exactly what was there
 * before (timestamp included). For a sign-in that has to write its credit
 * before it knows whether it worked (One Tap: the auth listener reads the
 * credit while the sign-in is still in flight), so a failure doesn't leave a
 * false credit behind for the next 24 hours.
 */
export function noteSignupSourceUndoable(source: SignupSource): () => void {
	const previous = readJSON<unknown>(KEY, null);
	noteSignupSource(source);
	return () => void writeJSON(KEY, previous);
}

/** The source a sign-up made now is credited to, or `null` for none. */
export function signupSource(now = Date.now()): SignupSource | null {
	const stored = readJSON<{ source?: unknown; at?: unknown } | null>(KEY, null);
	if (
		stored &&
		isSignupSource(stored.source) &&
		typeof stored.at === 'number' &&
		now >= stored.at &&
		now - stored.at < SOURCE_TTL_MS
	) {
		return stored.source;
	}
	return null;
}

/** Add `src=<source>` to a (login) href. */
export function withSource(href: string, source: SignupSource): string {
	return withParam(href, 'src', source);
}

const seen = new Set<string>();

/** Count a prompt as seen — once per page session per source. */
export function promptSeen(source: SignupSource): void {
	if (seen.has(source)) return;
	seen.add(source);
	track('Signup prompt seen', { source });
}

/**
 * `use:seenOnView={source}` on a prompt's button: counts it as seen the first
 * time at least half of it is on screen. Without IntersectionObserver (old
 * browsers, tests) it counts on mount.
 */
export const seenOnView: Action<Element, SignupSource> = (node, initial) => {
	let source = initial;
	if (typeof IntersectionObserver === 'undefined') {
		promptSeen(source);
		return { update: (next: SignupSource) => (source = next) };
	}
	const io = new IntersectionObserver(
		(entries) => {
			if (entries.some((e) => e.isIntersecting)) {
				promptSeen(source);
				io.disconnect();
			}
		},
		{ threshold: 0.5 }
	);
	io.observe(node);
	return {
		update: (next: SignupSource) => (source = next),
		destroy: () => io.disconnect()
	};
};

/** Count a sign-up attempt (form submitted, Google pressed). */
export function signupStarted(): void {
	track('Signup started', { source: signupSource() ?? 'none' });
}

/** Test seam: forget which prompts were seen this session. */
export function _resetSeen(): void {
	seen.clear();
}
