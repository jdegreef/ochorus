import { beforeEach, describe, expect, it, vi } from 'vitest';

// auth.expectedUser: who the home page DRAWS for. The stored supabase-js
// session's account until init() resolves, then exactly `user` — so a stored
// session the client finds revoked stops drawing the dashboard, and nothing
// stored is ever taken as signed in (`user` and the token stay null until the
// client restores the session).
let restored: { access_token: string; user: { email: string } } | null = null;
vi.mock('./supabase', () => ({
	authEnabled: true,
	supabase: () =>
		Promise.resolve({
			auth: {
				getSession: async () => ({ data: { session: restored } }),
				onAuthStateChange: () => ({ data: { subscription: { unsubscribe() {} } } })
			}
		})
}));
vi.mock('./api', () => ({
	apiFetch: async () => {
		throw new Error('offline');
	},
	setAuthTokenProvider: () => {}
}));
vi.mock('./readingSync', () => ({
	readingSync: {
		setSignedIn() {},
		mergeOnSignIn: async () => {},
		restoreStash() {},
		endSession() {}
	}
}));

const STORED = { access_token: 'old', refresh_token: 'r', user: { email: 'm@example.com' } };

async function freshAuth() {
	vi.resetModules();
	return (await import('./auth.svelte')).auth;
}

beforeEach(() => {
	localStorage.clear();
	restored = null;
});

describe('auth.expectedUser', () => {
	it('is the stored session before init, without signing anyone in', async () => {
		localStorage.setItem('sb-abcdefgh-auth-token', JSON.stringify(STORED));
		const auth = await freshAuth();
		expect(auth.expectedUser).toEqual({ email: 'm@example.com' });
		expect(auth.user).toBeNull();
		expect(auth.initialized).toBe(false);
	});

	it('is null before init with no stored session', async () => {
		const auth = await freshAuth();
		expect(auth.expectedUser).toBeNull();
	});

	it('follows the restored session once init resolves', async () => {
		localStorage.setItem('sb-abcdefgh-auth-token', JSON.stringify(STORED));
		restored = { access_token: 'new', user: { email: 'm@example.com' } };
		const auth = await freshAuth();
		void auth.expectedUser;
		await auth.init();
		expect(auth.expectedUser).toEqual({ email: 'm@example.com' });
	});

	it('drops a stored session the client finds revoked', async () => {
		localStorage.setItem('sb-abcdefgh-auth-token', JSON.stringify(STORED));
		const auth = await freshAuth();
		expect(auth.expectedUser).not.toBeNull();
		await auth.init(); // restored stays null: revoked
		expect(auth.expectedUser).toBeNull();
	});
});
