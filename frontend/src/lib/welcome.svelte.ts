import { browser } from '$app/environment';

/**
 * The once-only sign-up welcome (WelcomePalette): "choose your library".
 * Offered when a sign-in finds a brand-new account (auth's `fresh` — no saved
 * prefs yet), and put away for good the moment the reader picks or skips. A
 * flag in localStorage, so it survives the email-confirmation round trip and
 * a reload, and never comes back on this device once answered.
 */
const KEY = 'ochorus:welcome';

class Welcome {
	pending = $state(false);

	init() {
		if (!browser) return;
		try {
			this.pending = localStorage.getItem(KEY) === 'pending';
		} catch {
			/* storage blocked: no welcome is better than one that never leaves */
		}
	}

	/** A new account signed in. Ignored once the welcome has been answered. */
	offer() {
		if (!browser) return;
		try {
			if (localStorage.getItem(KEY) === 'done') return;
			localStorage.setItem(KEY, 'pending');
			this.pending = true;
		} catch {
			/* see init */
		}
	}

	/** Picked or skipped — either way, never ask again on this device. */
	done() {
		this.pending = false;
		if (!browser) return;
		try {
			localStorage.setItem(KEY, 'done');
		} catch {
			/* the card still closes for this visit */
		}
	}
}

export const welcome = new Welcome();
