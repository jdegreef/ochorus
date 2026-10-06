import { beforeEach, describe, expect, it, vi } from 'vitest';

// Control the Supabase client so we can assert exactly what `signUp` /
// `signInWithMagicLink` pass as options — the wiring that carries the
// sign-up-band attribution to the account (see signupBand.ts + accounts
// authentication). authEnabled must be true or the methods early-return.
const signUp = vi.fn().mockResolvedValue({ error: null });
const signInWithOtp = vi.fn().mockResolvedValue({ error: null });
const resend = vi.fn().mockResolvedValue({ error: null });
vi.mock('./supabase', () => ({
	authEnabled: true,
	supabase: () => Promise.resolve({ auth: { signUp, signInWithOtp, resend } })
}));

import { auth } from './auth.svelte';

beforeEach(() => {
	localStorage.clear();
	signUp.mockClear();
	signInWithOtp.mockClear();
	resend.mockClear();
});

/** The reader followed `source`'s prompt to the form (what /login records). */
const follow = (source: string) =>
	localStorage.setItem('ochorus:signup_source', JSON.stringify({ source, at: Date.now() }));

describe('sign-up carries the followed prompt as Supabase metadata', () => {
	it('attaches signup_variant to signUp when a prompt was followed', async () => {
		follow('habit');
		await auth.signUp('reader@example.com', 'pw');
		expect(signUp).toHaveBeenCalledWith(
			expect.objectContaining({
				options: expect.objectContaining({ data: { signup_variant: 'habit' } })
			})
		);
	});

	it('attaches it to the magic-link path too', async () => {
		follow('progress');
		await auth.signInWithMagicLink('reader@example.com');
		expect(signInWithOtp).toHaveBeenCalledWith(
			expect.objectContaining({
				options: expect.objectContaining({ data: { signup_variant: 'progress' } })
			})
		);
	});

	it('omits data entirely when no prompt was followed', async () => {
		await auth.signUp('reader@example.com', 'pw');
		expect(signUp.mock.calls[0][0].options.data).toBeUndefined();
	});

	it('never forwards a junk stored value', async () => {
		localStorage.setItem(
			'ochorus:signup_source',
			JSON.stringify({ source: 'not-a-real-variant', at: Date.now() })
		);
		await auth.signUp('reader@example.com', 'pw');
		expect(signUp.mock.calls[0][0].options.data).toBeUndefined();
	});
});

describe('emailed links return to the page the reader was on', () => {
	const here = `${window.location.origin}/books/humility?plan=x`;
	const redirect = (fn: ReturnType<typeof vi.fn>) => fn.mock.calls[0][0].options.emailRedirectTo;

	it('passes a same-origin returnTo through, on every email it sends', async () => {
		await auth.signUp('reader@example.com', 'pw', here);
		await auth.signInWithMagicLink('reader@example.com', '/books/humility?plan=x');
		await auth.resendSignup('reader@example.com', here);
		expect(redirect(signUp)).toBe(here);
		expect(redirect(signInWithOtp)).toBe(here);
		expect(redirect(resend)).toBe(here);
		expect(resend.mock.calls[0][0].type).toBe('signup');
	});

	it('falls back to the site root for an off-site or missing returnTo', async () => {
		await auth.signUp('reader@example.com', 'pw', 'https://evil.test/phish');
		await auth.signInWithMagicLink('reader@example.com');
		expect(redirect(signUp)).toBe(window.location.origin);
		expect(redirect(signInWithOtp)).toBe(window.location.origin);
	});
});
