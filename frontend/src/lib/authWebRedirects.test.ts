import { beforeEach, describe, expect, it, vi } from 'vitest';

/**
 * The website's side of what the app changed (authApp.app.test.ts): its emailed
 * links still come back to this origin, Google is still offered, and its
 * passwordless email is a link, not a code.
 */
const sb = vi.hoisted(() => ({ resetPasswordForEmail: vi.fn() }));
vi.mock('./supabase', () => ({
	authEnabled: true,
	supabase: () => Promise.resolve({ auth: sb })
}));

const { auth } = await import('./auth.svelte');

beforeEach(() => {
	sb.resetPasswordForEmail.mockReset().mockResolvedValue({ error: null });
});

describe('auth on the website', () => {
	it('offers Google and emailed links', () => {
		expect(auth.googleEnabled).toBe(true);
		expect(auth.emailCodes).toBe(false);
	});

	it('lands a password reset back on this origin', async () => {
		await auth.sendPasswordReset('grace@example.org');
		expect(sb.resetPasswordForEmail).toHaveBeenCalledWith('grace@example.org', {
			redirectTo: `${window.location.origin}/reset-password`
		});
	});
});
