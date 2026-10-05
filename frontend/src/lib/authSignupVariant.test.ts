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
