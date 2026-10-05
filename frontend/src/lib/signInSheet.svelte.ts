import { auth } from './auth.svelte';
import { noteSignupSource, type SignupSource } from './signupSource';

/**
 * The sign-up panel over the current page (SignInSheet, mounted once in the
 * root layout). A prompt opens it instead of navigating to /login, so the
 * reader is still in their chapter when the account exists.
 *
 * Prompts keep a real /login href: a modified click (new tab), no JS, or auth
 * not configured all fall through to the page. `openFrom` is the click
 * handler that decides.
 */
class SignInSheet {
	open = $state(false);
	source = $state<SignupSource | null>(null);

	show(source: SignupSource) {
		noteSignupSource(source);
		this.source = source;
		this.open = true;
	}

	close() {
		this.open = false;
	}
}

export const signInSheet = new SignInSheet();

/**
 * `onclick={(e) => openFrom(e, 'footer')}` on a prompt's sign-up link: open the
 * panel in place of following the link, when that makes sense.
 */
export function openFrom(e: MouseEvent, source: SignupSource): void {
	if (!auth.enabled || !auth.initialized || auth.user) return;
	if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
	e.preventDefault();
	// Next tick: a prompt inside another sheet (the phone More sheet) closes
	// that one on the same click; opening after it has let go keeps the two
	// focus traps from fighting, and Escape returns focus somewhere real.
	setTimeout(() => signInSheet.show(source), 0);
}
