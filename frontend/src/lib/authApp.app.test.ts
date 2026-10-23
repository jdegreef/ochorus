import { beforeEach, describe, expect, it, vi } from 'vitest';

/**
 * The auth layer as the phone app's bundle sees it (the rest of the suite runs
 * the website's — vitest.config.ts pins `__APP__` false). In the app the page's
 * origin is capacitor://localhost, which is not a web address: every emailed
 * link must point at the website, and the reader signs in with the email's code.
 */
vi.mock('./platform', () => ({ IS_APP: true, APP_ASSET_ORIGIN: 'https://ochorus.com' }));
vi.mock('./config', () => ({ SITE_URL: 'https://ochorus.com', API_BASE_URL: '' }));

const sb = vi.hoisted(() => ({
	signUp: vi.fn(),
	signInWithOtp: vi.fn(),
	resend: vi.fn(),
	resetPasswordForEmail: vi.fn(),
	verifyOtp: vi.fn()
}));
vi.mock('./supabase', () => ({
	authEnabled: true,
	supabase: () => Promise.resolve({ auth: sb })
}));

const { auth } = await import('./auth.svelte');

beforeEach(() => {
	localStorage.clear();
	for (const f of Object.values(sb)) f.mockReset().mockResolvedValue({ error: null });
});

const here = `${window.location.origin}/es/books/humility?plan=x#c2`;

describe('auth in the app', () => {
	it('signs in by code, without Google', () => {
		expect(auth.emailCodes).toBe(true);
		expect(auth.googleEnabled).toBe(false);
	});

	it('points every emailed link at the same page on the website', async () => {
		await auth.signUp('grace@example.org', 'pw', here);
		await auth.signInWithMagicLink('grace@example.org', here);
		await auth.resendSignup('grace@example.org', here);
		const site = 'https://ochorus.com/es/books/humility?plan=x#c2';
		expect(sb.signUp.mock.calls[0][0].options.emailRedirectTo).toBe(site);
		expect(sb.signInWithOtp.mock.calls[0][0].options.emailRedirectTo).toBe(site);
		expect(sb.resend.mock.calls[0][0].options.emailRedirectTo).toBe(site);
	});

	it('falls back to the website, never the app origin', async () => {
		await auth.signUp('grace@example.org', 'pw');
		await auth.signInWithMagicLink('grace@example.org', 'https://evil.test/x');
		expect(sb.signUp.mock.calls[0][0].options.emailRedirectTo).toBe('https://ochorus.com');
		expect(sb.signInWithOtp.mock.calls[0][0].options.emailRedirectTo).toBe('https://ochorus.com');
	});

	it('sends the code email with the website’s sign-up rules (creates the account)', async () => {
		await auth.signInWithMagicLink('grace@example.org');
		const opts = sb.signInWithOtp.mock.calls[0][0].options;
		// Same as the website: no shouldCreateUser override.
		expect(opts.shouldCreateUser).toBeUndefined();
	});

	it('finishes a password reset on the website', async () => {
		await auth.sendPasswordReset('grace@example.org');
		expect(sb.resetPasswordForEmail).toHaveBeenCalledWith('grace@example.org', {
			redirectTo: 'https://ochorus.com/reset-password'
		});
	});

	it('verifies the emailed code, ignoring spaces typed into it', async () => {
		expect(await auth.verifyEmailCode('grace@example.org', '123 456', 'email')).toBeNull();
		expect(sb.verifyOtp).toHaveBeenCalledWith({ email: 'grace@example.org', token: '123456', type: 'email' });
		await auth.verifyEmailCode('grace@example.org', '654321', 'signup');
		expect(sb.verifyOtp).toHaveBeenLastCalledWith({
			email: 'grace@example.org',
			token: '654321',
			type: 'signup'
		});
	});

	it('returns a wrong code’s error code (never an empty string)', async () => {
		sb.verifyOtp.mockResolvedValue({ error: { code: 'otp_expired' } });
		expect(await auth.verifyEmailCode('grace@example.org', '000000', 'email')).toBe('otp_expired');
		sb.verifyOtp.mockResolvedValue({ error: { code: '' } });
		expect(await auth.verifyEmailCode('grace@example.org', '000000', 'email')).toBe('unexpected_failure');
	});
});
