import { env } from '$env/dynamic/public';
import { deLocalizeHref } from '$lib/paraglide/runtime';
import { auth } from '$lib/auth.svelte';
import { noteSignupSourceUndoable } from '$lib/signupSource';
import { signInSheet } from '$lib/signInSheet.svelte';

/**
 * Google One Tap: the "Continue as Grace" prompt Google shows a reader who is
 * already signed in to Google. One tap, no form, no email round trip — and
 * the account is made (or signed in) without leaving the page.
 *
 * Env-gated like Plausible ($lib/analytics): the root layout mounts OneTap only
 * when PUBLIC_GOOGLE_CLIENT_ID is set, so until then nothing loads and no
 * request goes to Google (render.yaml says where the ID comes from and the two
 * dashboard settings it needs).
 *
 * The flow: load Google's script, hand it the SHA-256 of a fresh random nonce,
 * and prompt. When the reader taps, Google returns a signed ID token carrying
 * that hash; Supabase checks it against the raw nonce (signInWithIdToken) and
 * returns a session. The auth listener then does what it does for any sign-in.
 * Google decides whether to show the prompt at all, and backs off by itself
 * after the reader closes it, so this only says when we would like to ask.
 */

const CLIENT_ID = env.PUBLIC_GOOGLE_CLIENT_ID?.trim() || '';

/** True only when this deploy has a Google client ID. */
export const ONE_TAP_ENABLED = CLIENT_ID !== '';

const GSI_SRC = 'https://accounts.google.com/gsi/client';

/**
 * Pages that already ask in their own way, or where a prompt would intrude.
 * The young-reader shelves and the For Children / For Teens editions (slug
 * suffix, see CLAUDE.md "young-reader edition") are quiet too: a one-tap
 * account offer for whichever Google account the device holds is not
 * something to put in front of a child.
 */
const QUIET_PREFIXES = ['/login', '/reset-password', '/welcome', '/admin', '/email', '/young-readers', '/teens'];
const YOUNG_EDITION = /^\/books\/[^/]+-(children|teens)(\/|$)/;

/** Would we ask on this page? (Signed-in state is the caller's to check.) */
export function oneTapAllowedOn(pathname: string): boolean {
	const path = deLocalizeHref(pathname);
	if (YOUNG_EDITION.test(path)) return false;
	return !QUIET_PREFIXES.some((p) => path === p || path.startsWith(`${p}/`));
}

/** A random nonce and the SHA-256 hex Google is given in its place. */
export async function makeNonce(): Promise<{ raw: string; hashed: string }> {
	const bytes = crypto.getRandomValues(new Uint8Array(32));
	const raw = btoa(String.fromCharCode(...bytes));
	const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(raw));
	const hashed = Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, '0')).join('');
	return { raw, hashed };
}

/**
 * Google answered with a credential: sign in with it. The `one_tap` credit is
 * written first, because a brand-new account is credited by the auth listener
 * while this sign-in is still in flight (a returning reader's sign-in is left
 * alone; attribution is fresh-account only, see auth). If the exchange fails,
 * the credit is undone and the sign-up panel opens, so the tap doesn't end in
 * nothing.
 */
export async function signInWithCredential(credential: string, rawNonce: string): Promise<string | null> {
	const undo = noteSignupSourceUndoable('one_tap');
	// No "Signup started" here: a credential can't tell a returning reader's
	// sign-in from a sign-up, so it would inflate starts. One Tap is judged by
	// the accounts credited to it (Admin → Users → Prompt funnel).
	const err = await auth.signInWithGoogleIdToken(credential, rawNonce);
	if (err) {
		undo();
		console.warn('One Tap sign-in failed:', err);
		signInSheet.open = true;
	}
	return err;
}

type GoogleId = {
	initialize(config: Record<string, unknown>): void;
	prompt(): void;
	cancel(): void;
};
const gsi = (): GoogleId | undefined =>
	(window as unknown as { google?: { accounts?: { id?: GoogleId } } }).google?.accounts?.id;

function loadScript(lang: string): Promise<void> {
	return new Promise<void>((resolve, reject) => {
		const s = document.createElement('script');
		// `hl`: the prompt speaks the page's language.
		s.src = `${GSI_SRC}?hl=${encodeURIComponent(lang)}`;
		s.async = true;
		s.onload = () => resolve();
		s.onerror = () => reject(new Error('Google sign-in script failed to load'));
		document.head.appendChild(s);
	});
}

let prompted = false;

/**
 * Ask once per page load. Safe to call repeatedly: later calls no-op. A script
 * that fails to load (a privacy extension, offline) isn't retried until the
 * next full load, so a blocker doesn't see a request on every navigation.
 */
export async function promptOneTap(lang: string): Promise<void> {
	if (prompted) return;
	prompted = true;
	try {
		await loadScript(lang);
		const id = gsi();
		if (!id) return;
		const nonce = await makeNonce();
		id.initialize({
			client_id: CLIENT_ID,
			nonce: nonce.hashed,
			callback: ({ credential }: { credential?: string }) => {
				if (credential) void signInWithCredential(credential, nonce.raw);
			},
			context: 'signin',
			auto_select: false,
			cancel_on_tap_outside: true,
			itp_support: true,
			// Chrome's replacement for third-party cookies: the browser's own
			// account chooser instead of Google's iframe.
			use_fedcm_for_prompt: true
		});
		id.prompt();
	} catch (e) {
		console.warn(e);
	}
}

/** Put the prompt away (the reader signed in another way, or moved somewhere quiet). */
export function cancelOneTap(): void {
	gsi()?.cancel();
}
