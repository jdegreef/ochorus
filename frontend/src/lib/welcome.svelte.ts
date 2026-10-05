import { browser } from '$app/environment';

/**
 * The once-only sign-up welcome (WelcomePalette): "choose your library".
 * Offered when a sign-in finds a brand-new account (auth's `fresh` — no saved
 * prefs yet), and put away for good the moment the reader picks or skips. A
 * flag in localStorage, so it survives the email-confirmation round trip and
 * a reload, and never comes back on this device once answered.
 */
const KEY = 'ochorus:welcome';
/**
 * The /welcome page, offered by the same fresh sign-in but answered
 * separately: the home dashboard sends a new reader there once, and opening
 * the page settles it. Its own key, because leaving the palette card
 * unanswered must not bounce the reader to /welcome on every visit home.
 */
const PAGE_KEY = 'ochorus:welcome-page';

class Welcome {
	pending = $state(false);
	/** The /welcome page is owed to this device's new account. */
	pagePending = $state(false);

	init() {
		if (!browser) return;
		try {
			this.pending = localStorage.getItem(KEY) === 'pending';
			this.pagePending = localStorage.getItem(PAGE_KEY) === 'pending';
		} catch {
			/* storage blocked: no welcome is better than one that never leaves */
		}
	}

	/** A new account signed in. Ignored once the welcome has been answered. */
	offer() {
		if (!browser) return;
		try {
			if (localStorage.getItem(PAGE_KEY) !== 'done') {
				localStorage.setItem(PAGE_KEY, 'pending');
				this.pagePending = true;
			}
			if (localStorage.getItem(KEY) === 'done') return;
			localStorage.setItem(KEY, 'pending');
			this.pending = true;
		} catch {
			/* see init */
		}
	}

	/**
	 * Sign-out: the page is owed to an ACCOUNT, so it must not carry over to
	 * whoever signs in next on this browser. (The palette card stays — it is a
	 * device preference, like the theme it sets.)
	 */
	forgetPage() {
		this.pagePending = false;
		if (!browser) return;
		try {
			localStorage.removeItem(PAGE_KEY);
		} catch {
			/* nothing stored to leak */
		}
	}

	/** The reader has opened /welcome — never send them there again. */
	pageSeen() {
		this.pagePending = false;
		if (!browser) return;
		try {
			localStorage.setItem(PAGE_KEY, 'done');
		} catch {
			/* the redirect still stops for this visit */
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
