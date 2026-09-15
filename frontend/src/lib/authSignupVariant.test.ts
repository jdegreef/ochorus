import { beforeEach, describe, expect, it, vi } from 'vitest';

// Control the Supabase client so we can assert exactly what `signUp` /
// `signInWithMagicLink` pass as options — the wiring that carries the
// sign-up-band attribution to the account (see signupBand.ts + accounts
// authentication). authEnabled must be true or the methods early-return.
const signUp = vi.fn().mockResolvedValue({ error: null });
const signInWithOtp = vi.fn().mockResolvedValue({ error: null });
vi.mock('./supabase', () => ({
	authEnabled: true,
	supabase: () => Promise.resolve({ auth: { signUp, signInWithOtp } })
}));

import { auth } from './auth.svelte';

beforeEach(() => {
	localStorage.clear();
	signUp.mockClear();
	signInWithOtp.mockClear();
});

describe('sign-up carries the shown band as Supabase metadata', () => {
	it('attaches signup_variant to signUp when a band was shown', async () => {
		localStorage.setItem('ochorus:signup_variant', JSON.stringify('habit'));
		await auth.signUp('reader@example.com', 'pw');
		expect(signUp).toHaveBeenCalledWith(
			expect.objectContaining({
				options: expect.objectContaining({ data: { signup_variant: 'habit' } })
			})
		);
	});

	it('attaches it to the magic-link path too', async () => {
		localStorage.setItem('ochorus:signup_variant', JSON.stringify('progress'));
		await auth.signInWithMagicLink('reader@example.com');
		expect(signInWithOtp).toHaveBeenCalledWith(
			expect.objectContaining({
				options: expect.objectContaining({ data: { signup_variant: 'progress' } })
			})
		);
	});

	it('omits data entirely when no band was shown', async () => {
		await auth.signUp('reader@example.com', 'pw');
		expect(signUp.mock.calls[0][0].options.data).toBeUndefined();
	});

	it('never forwards a junk stored value', async () => {
		localStorage.setItem('ochorus:signup_variant', JSON.stringify('not-a-real-variant'));
		await auth.signUp('reader@example.com', 'pw');
		expect(signUp.mock.calls[0][0].options.data).toBeUndefined();
	});
});
