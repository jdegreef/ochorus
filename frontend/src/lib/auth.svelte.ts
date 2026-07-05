import { browser } from '$app/environment';
import { apiFetch, setAuthTokenProvider } from './api';
import { authEnabled, supabase } from './supabase';
import { readerPrefs } from './readerPrefs.svelte';
import { theme } from './theme.svelte';
import { lang } from './lang.svelte';
import { i18n } from './i18n.svelte';
import { readingSync } from './readingSync';

export interface Profile {
	email: string;
	display_name: string;
	locale: string;
	theme: string;
	font_scale: number;
}

const NOT_CONFIGURED = 'Sign-in is not configured yet.';

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
	#token: string | null = null;
	#ready = false;
	#pushTimer: ReturnType<typeof setTimeout> | undefined;

	async init() {
		if (!browser || this.#ready) return;
		this.#ready = true;
		setAuthTokenProvider(() => this.#token);

		const sb = supabase();
		if (!sb) return;

		const { data } = await sb.auth.getSession();
		this.#applySession(data.session);
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
			}
		});
	}

	#applySession(session: { access_token: string; user: { email?: string } } | null) {
		this.#token = session?.access_token ?? null;
		this.user = session ? { email: session.user.email ?? '' } : null;
		readingSync.setSignedIn(!!session);
	}

	// Auth actions. Each returns an error message on failure, or null on success
	// (Google redirects away, so it never resolves to null on success).

	async signIn(email: string, password: string): Promise<string | null> {
		const sb = supabase();
		if (!sb) return NOT_CONFIGURED;
		const { error } = await sb.auth.signInWithPassword({ email, password });
		return error?.message ?? null;
	}

	async signUp(email: string, password: string): Promise<string | null> {
		const sb = supabase();
		if (!sb) return NOT_CONFIGURED;
		const { error } = await sb.auth.signUp({
			email,
			password,
			options: { emailRedirectTo: origin() }
		});
		return error?.message ?? null;
	}

	/** Passwordless: email the user a one-time sign-in link. */
	async signInWithMagicLink(email: string): Promise<string | null> {
		const sb = supabase();
		if (!sb) return NOT_CONFIGURED;
		const { error } = await sb.auth.signInWithOtp({
			email,
			options: { emailRedirectTo: origin() }
		});
		return error?.message ?? null;
	}

	/** OAuth via Google. On success the browser navigates away to Google. */
	async signInWithGoogle(): Promise<string | null> {
		const sb = supabase();
		if (!sb) return NOT_CONFIGURED;
		const { error } = await sb.auth.signInWithOAuth({
			provider: 'google',
			options: { redirectTo: origin() }
		});
		return error?.message ?? null;
	}

	/** Email a password-reset link that lands on /reset-password. */
	async sendPasswordReset(email: string): Promise<string | null> {
		const sb = supabase();
		if (!sb) return NOT_CONFIGURED;
		const redirectTo = browser ? `${window.location.origin}/reset-password` : undefined;
		const { error } = await sb.auth.resetPasswordForEmail(email, { redirectTo });
		return error?.message ?? null;
	}

	/** Set a new password during a recovery session (from the reset link). */
	async updatePassword(password: string): Promise<string | null> {
		const sb = supabase();
		if (!sb) return NOT_CONFIGURED;
		const { error } = await sb.auth.updateUser({ password });
		return error?.message ?? null;
	}

	async signOut() {
		await supabase()?.auth.signOut();
		this.user = null;
		this.#token = null;
	}

	/** Pull the saved profile and apply reading preferences locally. */
	async #pullProfile() {
		try {
			const p = await apiFetch<Profile>('/api/auth/me/');
			if (p.theme === 'dark' || p.theme === 'light') theme.set(p.theme);
			if (p.font_scale) readerPrefs.setScale(p.font_scale);
			if (p.locale) {
				lang.set(p.locale);
				i18n.set(p.locale);
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
					theme: theme.current,
					font_scale: readerPrefs.scale,
					locale: lang.current
				})
			}).catch(() => {});
		}, 600);
	}
}

export const auth = new Auth();
