import { beforeEach, describe, expect, it, vi } from 'vitest';

// Drive a full sign-in through init() so we exercise the real wiring that
// attributes an OAuth sign-up: #applySession captures the account's created_at,
// #pullProfile runs, and #recordSignupSource POSTs the stored band arm. Mocks
// are the seams around auth — the Supabase client, the API client, the reading
// sync — so the assertion is purely "did the sign-up-source POST fire".
const created_at = new Date().toISOString(); // brand-new account → within the freshness window
const session = { access_token: 'tok', user: { email: 'r@example.com', created_at } };

const getSession = vi.fn(async () => ({ data: { session } }));
const onAuthStateChange = vi.fn(() => ({ data: { subscription: { unsubscribe() {} } } }));
vi.mock('./supabase', () => ({
	authEnabled: true,
	supabase: () => Promise.resolve({ auth: { getSession, onAuthStateChange } })
}));

const apiFetch = vi.fn(async (url: string, _init?: { method?: string; body?: string }) =>
	url === '/api/auth/me/' ? { email: 'r@example.com' } : undefined
);
vi.mock('./api', () => ({
	apiFetch: (url: string, init?: { method?: string; body?: string }) => apiFetch(url, init),
	setAuthTokenProvider: () => {}
}));

vi.mock('./readingSync', () => ({
	readingSync: {
		setSignedIn() {},
		mergeOnSignIn: async () => {},
		clearOnSignOut() {},
		endSession() {},
		restoreStash() {},
		settle: async () => true,
		pushProgress() {},
		pushActivity() {},
		setFinished() {}
	}
}));

import { auth } from './auth.svelte';

beforeEach(() => localStorage.clear());

describe('#recordSignupSource wiring', () => {
	it('POSTs the shown band arm on a fresh sign-in (the OAuth attribution path)', async () => {
		localStorage.setItem('ochorus:signup_variant', JSON.stringify('library'));
		await auth.init();
		const call = apiFetch.mock.calls.find((c) => c[0] === '/api/auth/signup-source/');
		expect(call, 'expected a POST to /api/auth/signup-source/').toBeTruthy();
		expect(call![1]?.method).toBe('POST');
		expect(JSON.parse(call![1]?.body ?? '{}')).toEqual({ signup_variant: 'library' });
	});
});
