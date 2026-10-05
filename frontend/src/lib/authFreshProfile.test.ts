import { afterEach, beforeEach, describe, expect, it, vi, type MockInstance } from 'vitest';

// #pullProfile: an account with no saved prefs (blank theme) keeps and uploads
// the device's; an account with saved prefs still wins (cross-device restore).
const session = { access_token: 'tok', user: { email: 'r@example.com', created_at: '' } };
vi.mock('./supabase', () => ({
	authEnabled: true,
	supabase: () =>
		Promise.resolve({
			auth: {
				getSession: async () => ({ data: { session } }),
				onAuthStateChange: () => ({ data: { subscription: { unsubscribe() {} } } })
			}
		})
}));

let profile: Record<string, unknown> = {};
const apiFetch = vi.fn(async (url: string, init?: { method?: string; body?: string }) =>
	url === '/api/auth/me/' && !init?.method ? profile : undefined
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

async function signIn(beforeInit?: () => Promise<void>) {
	vi.resetModules();
	const { theme } = await import('./theme.svelte');
	theme.init();
	await beforeInit?.();
	const { auth } = await import('./auth.svelte');
	await auth.init();
	return theme;
}

beforeEach(() => {
	localStorage.clear();
	vi.stubGlobal('matchMedia', (q: string) => ({ matches: false, media: q, addEventListener() {}, removeEventListener() {} }));
	apiFetch.mockClear();
	vi.useFakeTimers();
});

afterEach(() => {
	vi.useRealTimers();
	vi.unstubAllGlobals();
	window.history.replaceState(null, '', '/');
});

describe('#pullProfile and the reader’s theme', () => {
	it('keeps (and uploads) the device theme on a fresh account', async () => {
		localStorage.setItem('theme', 'dark');
		profile = { email: 'r@example.com', theme: '', font_scale: 1, tts_rate: 1 };
		const theme = await signIn();
		expect(theme.preference).toBe('dark');
		vi.advanceTimersByTime(1000);
		const push = apiFetch.mock.calls.find((c) => c[1]?.method === 'PATCH' && c[1].body?.includes('theme'));
		expect(push, 'expected the device prefs to be pushed').toBeTruthy();
		expect(JSON.parse(push![1]!.body!).theme).toBe('dark');
	});

	it('does not bounce a fresh account out of the page language', async () => {
		window.history.replaceState(null, '', '/es/');
		profile = { email: 'r@example.com', theme: '', locale: 'en' };
		let set: MockInstance | undefined;
		await signIn(async () => {
			const { lang } = await import('./lang.svelte');
			set = vi.spyOn(lang, 'set');
		});
		expect(set).not.toHaveBeenCalled();
	});

	it('offers the sign-up welcome to a fresh account only', async () => {
		profile = { email: 'r@example.com', theme: '' };
		await signIn();
		const { welcome } = await import('./welcome.svelte');
		expect(welcome.pending).toBe(true);
		expect(welcome.pagePending).toBe(true);

		localStorage.clear();
		profile = { email: 'r@example.com', theme: 'light' };
		await signIn();
		const again = await import('./welcome.svelte');
		expect(again.welcome.pending).toBe(false);
	});

	it('adopts a saved account theme', async () => {
		localStorage.setItem('theme', 'dark');
		profile = { email: 'r@example.com', theme: 'sepia', font_scale: 1, tts_rate: 1 };
		const theme = await signIn();
		expect(theme.preference).toBe('sepia');
	});
});
