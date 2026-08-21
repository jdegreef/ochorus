/**
 * Supabase auth failures, as something a reader can actually read.
 *
 * The auth calls used to hand their `error.message` straight to the page, so a
 * failed sign-in rendered Supabase's own English — "Invalid login credentials",
 * "User already registered" — inside a localized UI. Under `/ar` that is an
 * untranslated LTR sentence dropped into an RTL page, on the one screen where a
 * reader is deciding whether to trust the site with a password.
 *
 * So the auth layer returns a CODE and this maps it to a catalogue key. Codes
 * are stable API contract (`AuthError.code`); messages are prose the vendor can
 * reword in any release.
 *
 * The map is deliberately many-to-few. A reader does not need twenty distinct
 * sentences — they need to know whether to retype something, go to their inbox,
 * or wait. Anything unrecognised (including a genuinely unexpected failure)
 * lands on the generic key rather than leaking a raw string.
 */

/** Our own codes, for failures that never reach Supabase. */
export const AUTH_NOT_CONFIGURED = 'not_configured';

const KEYS: Record<string, string> = {
	// Nothing to sign in with — no Supabase project is wired up in this build.
	[AUTH_NOT_CONFIGURED]: 'authErr.notConfigured',

	// Wrong email/password. Only reachable from a form that HAS both.
	invalid_credentials: 'authErr.invalidCredentials',

	// The address itself is malformed. Kept separate because the reset and
	// magic-link forms have no password field, and telling someone their
	// password is wrong on a form without one is worse than saying nothing.
	validation_failed: 'authErr.invalidEmail',
	email_address_invalid: 'authErr.invalidEmail',

	// The account exists but the email link hasn't been followed yet.
	email_not_confirmed: 'authErr.emailNotConfirmed',

	// Signing up with an address that already has an account.
	user_already_exists: 'authErr.emailExists',
	email_exists: 'authErr.emailExists',

	// Password rejected on sign-up or reset.
	weak_password: 'authErr.weakPassword',
	same_password: 'authErr.samePassword',

	// Throttled. All three rate limits say the same thing to a reader: wait.
	over_email_send_rate_limit: 'authErr.rateLimited',
	over_request_rate_limit: 'authErr.rateLimited',
	over_sms_send_rate_limit: 'authErr.rateLimited',

	// NOTE: no `otp_expired`. An expired magic/reset link never reaches these
	// functions — Supabase reports it on the redirect back, and the recovery
	// session simply comes up missing (AuthSessionMissingError, no `code`). A
	// mapping for it would be a string nothing can ever render.

	// Sign-up is switched off for this project.
	signup_disabled: 'authErr.signupDisabled',
	email_provider_disabled: 'authErr.signupDisabled'
};

/**
 * The catalogue key for an auth failure code.
 *
 * Pass the code through `i18n.t()` at the call site — this stays pure so the
 * mapping can be tested without a locale loaded.
 */
export function authErrorKey(code: string | null | undefined): string {
	return (code && KEYS[code]) || 'authErr.generic';
}
