/**
 * The auth-failure map.
 *
 * The property that matters is the fallback: an unrecognised code must never
 * fall through to nothing, because the alternative the page had was rendering
 * Supabase's raw English into a localized (sometimes RTL) UI.
 */
import { describe, expect, it } from 'vitest';
import { authErrorKey, AUTH_NOT_CONFIGURED } from './authErrors';

describe('authErrorKey', () => {
	it('names the common failures', () => {
		expect(authErrorKey('invalid_credentials')).toBe('authErr.invalidCredentials');
		expect(authErrorKey('email_not_confirmed')).toBe('authErr.emailNotConfirmed');
		expect(authErrorKey('user_already_exists')).toBe('authErr.emailExists');
		expect(authErrorKey('weak_password')).toBe('authErr.weakPassword');
	});

	it('keeps a bad address apart from a bad password', () => {
		// The reset and magic-link forms have no password field, so
		// "email and password don't match" would be nonsense on them.
		expect(authErrorKey('validation_failed')).toBe('authErr.invalidEmail');
		expect(authErrorKey('email_address_invalid')).toBe('authErr.invalidEmail');
		expect(authErrorKey('invalid_credentials')).toBe('authErr.invalidCredentials');
	});

	it('collapses the three rate limits onto one message', () => {
		// A reader does not care which quota they hit; they care that waiting
		// is the fix.
		const keys = [
			'over_email_send_rate_limit',
			'over_request_rate_limit',
			'over_sms_send_rate_limit'
		].map(authErrorKey);
		expect(new Set(keys).size).toBe(1);
		expect(keys[0]).toBe('authErr.rateLimited');
	});

	it('treats "there is no Supabase project" as its own case', () => {
		// A dev build with no keys must not tell the reader their password is wrong.
		expect(authErrorKey(AUTH_NOT_CONFIGURED)).toBe('authErr.notConfigured');
	});

	it('falls back rather than leaking an unmapped code', () => {
		expect(authErrorKey('some_future_supabase_code')).toBe('authErr.generic');
		expect(authErrorKey('')).toBe('authErr.generic');
		expect(authErrorKey(null)).toBe('authErr.generic');
		expect(authErrorKey(undefined)).toBe('authErr.generic');
	});

	it('never returns a raw vendor message', () => {
		// The bug this replaced: `error.message` reaching the page verbatim.
		expect(authErrorKey('Invalid login credentials')).toBe('authErr.generic');
	});
});
