import { browser } from '$app/environment';
import { AUTH_NOT_CONFIGURED } from './authErrors';
import { apiFetch, setAuthTokenProvider } from './api';
import { authEnabled, supabase } from './supabase';
import { readerPrefs } from './readerPrefs.svelte';
import { listen } from './listen.svelte';
import { theme, normalizePref } from './theme.svelte';
import { lang } from './lang.svelte';
import { readingSync } from './readingSync';

export interface Profile {
	email: string;
	display_name: string;
	locale: string;
	theme: string;
	font_scale: number;
	tts_rate?: number;
	tts_voice_uri?: string;
	is_admin?: boolean;
}

// A CODE, not a sentence: the page localizes it (see $lib/authErrors).
const NOT_CONFIGURED = AUTH_NOT_CONFIGURED;

/** Absolute app origin for redirect URLs (magic link / OAuth land back here). */
const origin = () => (browser ? window.location.origin : undefined);

/**
 * Auth + cross-device preference sync. Supabase owns the credentials; on sign-in
 * we pull the Django-side profile (reading prefs) and apply it, and we push prefs
 * back when they change. Everything degrades gracefully when auth is unconfigured.
 */
class Auth {
	enabled = authEnabled;
	user = $state<{ email: string } | null>(null);
	// The reader's chosen display name (from the profile); '' when unset — callers
	// fall back to the email. Kept separate from `user` (which mirrors the session).
	displayName = $state('');
	// Whether the signed-in user may see the /admin dashboard (from the profile).
	isAdmin = $state(false);
	// True once the initial session has been resolved (or auth is unconfigured),
	// so callers can wait before making authenticated requests rather than firing
	// a premature unauthenticated one on a fresh page load.
	initialized = $state(false);
	#token: string | null = null;
	#ready = false;
	#pushTimer: ReturnType<typeof setTimeout> | undefined;

	async init() {
		if (!browser || this.#ready) return;
		this.#ready = true;
		setAuthTokenProvider(() => this.#token);

		const sb = supabase();
		if (!sb) {
			this.initialized = true; // auth unconfigured — nothing to restore
			return;
		}

		const { data } = await sb.auth.getSession();
		this.#applySession(data.session);
		this.initialized = true; // session resolved and token attached (if any)
		if (data.session) {
			await this.#pullProfile();
			await readingSync.mergeOnSignIn();
		}

		sb.auth.onAuthStateChange((_event, session) => {
			const wasSignedIn = !!this.user;
			this.#applySession(session);
			if (session && !wasSignedIn) {
				this.#pullProfile();
				readingSync.mergeOnSignIn();
			} else if (!session && wasSignedIn) {
				// The session ended for ANY reason — token expiry/revocation, a
				// sign-out in another tab, a password change — not only the explicit
				// signOut() button. Wipe this reader's data from the device so it
				// isn't merged into the next account on a shared browser. Idempotent,
				// so signOut() calling clearOnSignOut() too is harmless.
				clearTimeout(this.#pushTimer);
				this.displayName = '';
				this.isAdmin = false;
				readingSync.clearOnSignOut();
			}
		});
	}

	#applySession(session: { access_token: string; user: { email?: string } } | null) {
		this.#token = session?.access_token ?? null;
		this.user = session ? { email: session.user.email ?? '' } : null;
		if (!session) this.isAdmin = false;
		readingSync.setSignedIn(!!session);
	}

	// Auth actions. Each returns an error CODE on failure, or null on success
	// (Google redirects away, so it never resolves to null on success).
	//
	// A code, not `error.message`: the message is Supabase's own English prose,
	// and handing it to the page put untranslated (sometimes LTR-in-RTL) text on
	// the one screen asking for a password. `authErrorKey()` turns the code into
	// a catalogue key.

	async signIn(email: string, password: string): Promise<string | null> {
		const sb = supabase();
		if (!sb) return NOT_CONFIGURED;
		const { error } = await sb.auth.signInWithPassword({ email, password });
		// `||`, not `??`: an AuthError with an empty-string code would otherwise
		// return '' — which every caller's `if (err)` reads as SUCCESS, silently
		// clearing the password field and showing nothing.
		return error ? error.code || 'unexpected_failure' : null;
	}

	async signUp(email: string, password: string): Promise<string | null> {
		const sb = supabase();
		if (!sb) return NOT_CONFIGURED;
		const { error } = await sb.auth.signUp({
			email,
			password,
			options: { emailRedirectTo: origin() }
		});
		// `||`, not `??`: an AuthError with an empty-string code would otherwise
		// return '' — which every caller's `if (err)` reads as SUCCESS, silently
		// clearing the password field and showing nothing.
		return error ? error.code || 'unexpected_failure' : null;
	}

	/** Passwordless: email the user a one-time sign-in link. */
	async signInWithMagicLink(email: string): Promise<string | null> {
		const sb = supabase();
		if (!sb) return NOT_CONFIGURED;
		const { error } = await sb.auth.signInWithOtp({
			email,
			options: { emailRedirectTo: origin() }
		});
		// `||`, not `??`: an AuthError with an empty-string code would otherwise
		// return '' — which every caller's `if (err)` reads as SUCCESS, silently
		// clearing the password field and showing nothing.
		return error ? error.code || 'unexpected_failure' : null;
	}

	/** OAuth via Google. On success the browser navigates away to Google. */
	async signInWithGoogle(): Promise<string | null> {
		const sb = supabase();
		if (!sb) return NOT_CONFIGURED;
		const { error } = await sb.auth.signInWithOAuth({
			provider: 'google',
			options: { redirectTo: origin() }
		});
		// `||`, not `??`: an AuthError with an empty-string code would otherwise
		// return '' — which every caller's `if (err)` reads as SUCCESS, silently
		// clearing the password field and showing nothing.
		return error ? error.code || 'unexpected_failure' : null;
	}

	/** Email a password-reset link that lands on /reset-password. */
	async sendPasswordReset(email: string): Promise<string | null> {
		const sb = supabase();
		if (!sb) return NOT_CONFIGURED;
		const redirectTo = browser ? `${window.location.origin}/reset-password` : undefined;
		const { error } = await sb.auth.resetPasswordForEmail(email, { redirectTo });
		// `||`, not `??`: an AuthError with an empty-string code would otherwise
		// return '' — which every caller's `if (err)` reads as SUCCESS, silently
		// clearing the password field and showing nothing.
		return error ? error.code || 'unexpected_failure' : null;
	}

	/** Set a new password during a recovery session (from the reset link). */
	async updatePassword(password: string): Promise<string | null> {
		const sb = supabase();
		if (!sb) return NOT_CONFIGURED;
		const { error } = await sb.auth.updateUser({ password });
		// `||`, not `??`: an AuthError with an empty-string code would otherwise
		// return '' — which every caller's `if (err)` reads as SUCCESS, silently
		// clearing the password field and showing nothing.
		return error ? error.code || 'unexpected_failure' : null;
	}

	async signOut() {
		// Cancel a pending prefs push — it would fire after the token is gone.
		clearTimeout(this.#pushTimer);
		await supabase()?.auth.signOut();
		this.user = null;
		this.#token = null;
		this.isAdmin = false;
		this.displayName = '';
		// Wipe this user's reading data from the device: on a shared browser it
		// would otherwise be merged into the next account that signs in.
		readingSync.clearOnSignOut();
	}

	/** Pull the saved profile and apply reading preferences locally. */
	async #pullProfile() {
		try {
			const p = await apiFetch<Profile>('/api/auth/me/');
			this.isAdmin = !!p.is_admin;
			this.displayName = p.display_name || '';
			if (typeof p.theme === 'string' && p.theme) theme.set(normalizePref(p.theme));
			if (p.font_scale) readerPrefs.setScale(p.font_scale);
			// Listening prefs: rate always applies; a voiceURI only resolves if the
			// device actually has that voice (best-effort across devices).
			if (typeof p.tts_rate === 'number') listen.setRate(p.tts_rate);
			if (typeof p.tts_voice_uri === 'string') listen.setVoice(p.tts_voice_uri);
			// Language: a locale the reader explicitly picked on this device wins
			// over the synced profile (otherwise the profile would bounce them back
			// out of the language they just chose). When they have such a choice,
			// reconcile the profile to it so their other devices follow. Only on a
			// device with no local choice do we adopt the saved profile locale
			// (cross-device restore) — and only if it's a language we still offer.
			const chosen = lang.chosen();
			if (chosen) {
				if (p.locale !== lang.current) this.pushPrefs();
			} else if (p.locale && lang.isAvailable(p.locale)) {
				lang.set(p.locale);
			}
		} catch {
			/* first-time profile or API down — keep local prefs */
		}
	}

	/** Debounced push of the current local prefs to the profile. */
	pushPrefs() {
		if (!this.user) return;
		clearTimeout(this.#pushTimer);
		this.#pushTimer = setTimeout(() => {
			apiFetch('/api/auth/me/', {
				method: 'PATCH',
				body: JSON.stringify({
					theme: theme.preference,
					font_scale: readerPrefs.scale,
					tts_rate: listen.rate,
					tts_voice_uri: listen.voiceURI,
					locale: lang.current
				})
			}).catch(() => {});
		}, 600);
	}

	/**
	 * Save the display name to the profile. Updates local state optimistically so
	 * the greeting changes immediately; a failed request leaves the server as-is
	 * (the next profile pull reconciles). `name` is trimmed; '' clears it.
	 */
	async setDisplayName(name: string) {
		if (!this.user) return;
		const trimmed = name.trim().slice(0, 120);
		this.displayName = trimmed;
		try {
			await apiFetch('/api/auth/me/', {
				method: 'PATCH',
				body: JSON.stringify({ display_name: trimmed })
			});
		} catch {
			/* offline or API down — keep the optimistic value for this session */
		}
	}

	/**
	 * Delete the account: erase all server-side reading data (the profile and,
	 * via CASCADE, progress/highlights/favorites), then sign out — which also
	 * wipes the local cache. Resolves false if there's no session or the request
	 * fails (so the UI can keep the reader on the page).
	 */
	async deleteAccount(): Promise<boolean> {
		if (!this.user) return false;
		try {
			await apiFetch('/api/auth/me/', { method: 'DELETE' });
		} catch {
			return false;
		}
		await this.signOut();
		return true;
	}
}

export const auth = new Auth();
