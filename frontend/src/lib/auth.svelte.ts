import { browser } from '$app/environment';
import { AUTH_NOT_CONFIGURED } from './authErrors';
import { apiFetch, setAuthTokenProvider } from './api';
import { authEnabled, supabase } from './supabase';
import { readerPrefs } from './readerPrefs.svelte';
import { listen } from './listen.svelte';
import { theme, normalizePref } from './theme.svelte';
import { lang } from './lang.svelte';
import { readingSync } from './readingSync';
import { shownVariant } from './signupBand';
import { type AdminScope, type Scopes, can as canDo, hasAnyAdminAccess } from './adminAccess';

export interface Profile {
	email: string;
	display_name: string;
	locale: string;
	theme: string;
	font_scale: number;
	tts_rate?: number;
	tts_voice_uri?: string;
	timezone?: string;
	is_admin?: boolean;
	is_super_admin?: boolean;
	roles?: string[];
	// A super admin gets the literal "all"; everyone else, their grant list.
	scopes?: AdminScope[] | 'all';
}

/** This browser's IANA timezone (e.g. "Europe/London"), or '' if unavailable. */
function deviceTimezone(): string {
	try {
		return Intl.DateTimeFormat().resolvedOptions().timeZone || '';
	} catch {
		return '';
	}
}

// A CODE, not a sentence: the page localizes it (see $lib/authErrors).
const NOT_CONFIGURED = AUTH_NOT_CONFIGURED;

/** Absolute app origin for redirect URLs (magic link / OAuth land back here). */
const origin = () => (browser ? window.location.origin : undefined);

/**
 * Supabase sign-up options carrying the sign-up-band attribution, or nothing.
 * `data` lands in the user's ``user_metadata`` (so it survives the email
 * confirmation round-trip) and Django records it create-only against the new
 * account. Only set when the reader actually saw a band — the backend also
 * validates the value, so a stale key can never corrupt the analytics.
 */
function signupMetadata(): { data?: { signup_variant: string } } {
	const variant = shownVariant();
	return variant ? { data: { signup_variant: variant } } : {};
}

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
	// Scoped admin capabilities (from the profile): 'all' for a super admin, else
	// the user's grants. Drives the capability-aware admin nav via `can()`. This
	// is UX only — the API enforces every request regardless.
	scopes = $state<Scopes>([]);
	// Any admin access at all — a super admin OR at least one grant. Gates the
	// "Admin" entry link (a scoped grantee isn't a super admin, so `isAdmin`
	// alone would hide the whole area from them).
	hasAdminAccess = $derived(hasAnyAdminAccess(this.scopes));
	// Sign-out was asked for while changes on this device hadn't reached the
	// account (offline, a failed push). The layout shows UnsyncedSignOutDialog.
	signOutBlocked = $state(false);
	// A "Language Admin": has admin access but isn't a super admin. Drives the
	// role-specific relabelling ("Language Admin" vs "Admin"), the trimmed
	// dashboard, and the language-admin manual link. UX only — the API enforces
	// every request regardless (import / queueing / PII are gated server-side).
	isLanguageAdmin = $derived(this.hasAdminAccess && !this.isAdmin);
	// The reader-facing name for this user's admin access — one source of truth for
	// the account-menu link, the nav-rail header and the dashboard heading.
	adminLabel = $derived(this.isLanguageAdmin ? 'Language Admin' : 'Admin');
	// True once the initial session has been resolved (or auth is unconfigured),
	// so callers can wait before making authenticated requests rather than firing
	// a premature unauthenticated one on a fresh page load.
	initialized = $state(false);
	#token: string | null = null;
	#ready = false;
	#pushTimer: ReturnType<typeof setTimeout> | undefined;
	/** The Supabase account's ISO creation time (for the new-vs-returning check
	 *  when attributing the sign-up band); null when signed out. */
	#userCreatedAt: string | null = null;
	/**
	 * Whether the account's saved preferences have been applied locally yet.
	 *
	 * `pushPrefs` is debounced 600 ms and fires from a layout effect that tracks
	 * `auth.user`, which `#applySession` sets BEFORE `#pullProfile` runs. On a
	 * slow connection the pull can take longer than the debounce, so the PATCH
	 * landed first and overwrote the account's saved theme, font scale and TTS
	 * voice with THIS DEVICE'S defaults. The pull then returned pre-PATCH values
	 * and restored them locally, so this device looked fine — while any other
	 * device reading the profile in that window got the clobbered values.
	 */
	#profileLoaded = false;

	/** Does the signed-in user hold `capability` at `verb` (in `language`, when the
	 *  action is language-scoped)? UX only — the API authorises every request. */
	can(capability: string, verb: string = 'view', language?: string): boolean {
		return canDo(this.scopes, capability, verb, language);
	}

	async init() {
		if (!browser || this.#ready) return;
		this.#ready = true;
		setAuthTokenProvider(() => this.#token);

		const sb = await supabase();
		if (!sb) {
			this.initialized = true; // auth unconfigured — nothing to restore
			return;
		}

		const { data } = await sb.auth.getSession();
		this.#applySession(data.session);
		this.initialized = true; // session resolved and token attached (if any)
		if (data.session) {
			await this.#pullProfile();
			readingSync.restoreStash(data.session.user.email ?? '');
			await readingSync.mergeOnSignIn();
		}

		sb.auth.onAuthStateChange((_event, session) => {
			const wasSignedIn = !!this.user;
			const endingEmail = this.user?.email ?? '';
			this.#applySession(session);
			if (session && !wasSignedIn) {
				this.#pullProfile();
				readingSync.restoreStash(session.user.email ?? '');
				readingSync.mergeOnSignIn();
			} else if (!session && wasSignedIn) {
				// The session ended for ANY reason — token expiry/revocation, a
				// sign-out in another tab, a password change — not only the explicit
				// signOut() button. Wipe this reader's data from the device so it
				// isn't merged into the next account on a shared browser. Idempotent,
				// so signOut() calling clearOnSignOut() too is harmless.
				clearTimeout(this.#pushTimer);
				// Re-gate: the next account's prefs must be read before anything
				// is pushed to it.
				this.#profileLoaded = false;
				this.displayName = '';
				this.isAdmin = false;
				this.scopes = [];
				// Not chosen by the reader (expiry, revocation, another tab): what
				// the account doesn't have yet is set aside for it, not lost. After
				// an explicit signOut() the device is already wiped, so this is a
				// plain second wipe.
				readingSync.endSession(endingEmail);
			}
		});
	}

	#applySession(
		session: { access_token: string; user: { email?: string; created_at?: string } } | null
	) {
		this.#token = session?.access_token ?? null;
		this.user = session ? { email: session.user.email ?? '' } : null;
		// The Supabase account's creation time, used only to tell a brand-new
		// sign-up from a returning login when attributing the sign-up band.
		this.#userCreatedAt = session?.user.created_at ?? null;
		if (!session) {
			this.isAdmin = false;
			this.scopes = [];
		}
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
		const sb = await supabase();
		if (!sb) return NOT_CONFIGURED;
		const { error } = await sb.auth.signInWithPassword({ email, password });
		// `||`, not `??`: an AuthError with an empty-string code would otherwise
		// return '' — which every caller's `if (err)` reads as SUCCESS, silently
		// clearing the password field and showing nothing.
		return error ? error.code || 'unexpected_failure' : null;
	}

	async signUp(email: string, password: string): Promise<string | null> {
		const sb = await supabase();
		if (!sb) return NOT_CONFIGURED;
		const { error } = await sb.auth.signUp({
			email,
			password,
			options: { emailRedirectTo: origin(), ...signupMetadata() }
		});
		// `||`, not `??`: an AuthError with an empty-string code would otherwise
		// return '' — which every caller's `if (err)` reads as SUCCESS, silently
		// clearing the password field and showing nothing.
		return error ? error.code || 'unexpected_failure' : null;
	}

	/** Passwordless: email the user a one-time sign-in link. */
	async signInWithMagicLink(email: string): Promise<string | null> {
		const sb = await supabase();
		if (!sb) return NOT_CONFIGURED;
		const { error } = await sb.auth.signInWithOtp({
			email,
			// `data` seeds user_metadata only when this link CREATES the account,
			// so it attributes a first-time sign-up and is ignored for a returning
			// reader — same create-only story as the password path.
			options: { emailRedirectTo: origin(), ...signupMetadata() }
		});
		// `||`, not `??`: an AuthError with an empty-string code would otherwise
		// return '' — which every caller's `if (err)` reads as SUCCESS, silently
		// clearing the password field and showing nothing.
		return error ? error.code || 'unexpected_failure' : null;
	}

	/** OAuth via Google. On success the browser navigates away to Google. */
	async signInWithGoogle(): Promise<string | null> {
		const sb = await supabase();
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
		const sb = await supabase();
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
		const sb = await supabase();
		if (!sb) return NOT_CONFIGURED;
		const { error } = await sb.auth.updateUser({ password });
		// `||`, not `??`: an AuthError with an empty-string code would otherwise
		// return '' — which every caller's `if (err)` reads as SUCCESS, silently
		// clearing the password field and showing nothing.
		return error ? error.code || 'unexpected_failure' : null;
	}

	/**
	 * Sign out — after getting this device's changes to the account. If some
	 * can't get there (offline), nothing happens yet: `signOutBlocked` asks the
	 * reader (UnsyncedSignOutDialog), who can retry or sign out with `force`,
	 * discarding them. Resolves true once signed out.
	 */
	async signOut({ force = false }: { force?: boolean } = {}): Promise<boolean> {
		if (!force && !(await readingSync.settle())) {
			this.signOutBlocked = true;
			return false;
		}
		this.signOutBlocked = false;
		// Cancel a pending prefs push — it would fire after the token is gone.
		clearTimeout(this.#pushTimer);
		// Wipe this user's reading data from the device (on a shared browser it
		// would otherwise be merged into the next account that signs in) BEFORE
		// the session ends: the auth listener that fires then finds nothing
		// unsynced, so it can't stash what the reader chose to discard.
		readingSync.clearOnSignOut();
		await (await supabase())?.auth.signOut();
		this.user = null;
		this.#token = null;
		this.isAdmin = false;
		this.scopes = [];
		this.displayName = '';
		return true;
	}

	/** Pull the saved profile and apply reading preferences locally. */
	async #pullProfile() {
		try {
			const p = await apiFetch<Profile>('/api/auth/me/');
			this.isAdmin = !!p.is_admin;
			this.scopes = p.scopes ?? [];
			this.displayName = p.display_name || '';
			if (typeof p.theme === 'string' && p.theme) theme.set(normalizePref(p.theme));
			if (p.font_scale) readerPrefs.setScale(p.font_scale);
			// Listening prefs: rate always applies; a voiceURI only resolves if the
			// device actually has that voice (best-effort across devices).
			if (typeof p.tts_rate === 'number') listen.setRate(p.tts_rate);
			if (typeof p.tts_voice_uri === 'string') listen.setVoice(p.tts_voice_uri);
			// The account's values are now the local values, so pushing is safe
			// again. Set BEFORE the language reconcile below, which pushes
			// deliberately. See #profileLoaded.
			this.#profileLoaded = true;
			// Record where this reader is signing in from (browser timezone →
			// approximate country in the admin analytics). Independent of the
			// prefs push, so it's safe regardless of #profileLoaded.
			this.#syncTimezone(p.timezone);
			this.#recordSignupSource();
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
			// Still open the gate: with no saved profile to clobber, this
			// device's prefs are the only ones there are, and a first sign-in
			// must be able to create the profile from them.
			this.#profileLoaded = true;
			// No saved value to compare against — pass undefined so a genuine
			// first sign-up still records its timezone (the PATCH creates the
			// profile). Harmless if the API is simply down (it's caught).
			this.#syncTimezone(undefined);
			this.#recordSignupSource();
		}
	}

	/**
	 * Attribute a NEW account to the sign-up band the reader saw, for providers
	 * that can't carry it in the JWT (OAuth). Fire-and-forget POST of the stored
	 * arm, gated to a genuinely fresh account (Supabase `created_at` within the
	 * window) so a returning reader's stale stored arm is never sent. The backend
	 * re-checks create-only + freshness, and email/magic-link accounts already
	 * carry their arm from the JWT, so this is a no-op for them.
	 */
	#recordSignupSource() {
		if (!this.user) return;
		const variant = shownVariant();
		if (!variant) return;
		const created = this.#userCreatedAt ? Date.parse(this.#userCreatedAt) : NaN;
		if (!Number.isFinite(created) || Date.now() - created > 15 * 60 * 1000) return;
		apiFetch('/api/auth/signup-source/', {
			method: 'POST',
			body: JSON.stringify({ signup_variant: variant })
		}).catch(() => {});
	}

	/**
	 * Persist this device's timezone to the profile when it differs from what's
	 * saved (or nothing is saved yet). Fire-and-forget and cheap: a no-op PATCH
	 * whenever the value already matches, so it doesn't write on every sign-in.
	 */
	#syncTimezone(saved: string | undefined) {
		if (!this.user) return;
		const tz = deviceTimezone();
		if (!tz || tz === saved) return;
		apiFetch('/api/auth/me/', {
			method: 'PATCH',
			body: JSON.stringify({ timezone: tz })
		}).catch(() => {});
	}

	/** Debounced push of the current local prefs to the profile. */
	pushPrefs() {
		// Never push over an account whose saved prefs have not been read yet.
		if (!this.user || !this.#profileLoaded) return;
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
		// The account is gone, so nothing can sync to it: don't ask.
		await this.signOut({ force: true });
		return true;
	}
}

export const auth = new Auth();
