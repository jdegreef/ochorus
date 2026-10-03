import { beforeEach, describe, expect, it, vi } from 'vitest';

// A reader in dark mode signs up with Google: the brand-new profile used to come
// back with the model's default theme ("paper") and #pullProfile applied it, so
// the site turned light the moment they signed in (QA report, 2026-10). A blank
// theme now marks an account with no saved prefs: the device keeps its own and
// pushes them up. An account that HAS saved prefs still wins (cross-device).
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
const apiFetch = vi.fn(async (url: string, _init?: { method?: string; body?: string }) =>
	url === '/api/auth/me/' && !_init?.method ? profile : undefined
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
	window.matchMedia ??= ((q: string) =>
		({ matches: false, media: q, addEventListener() {}, removeEventListener() {} }) as unknown as MediaQueryList);
	apiFetch.mockClear();
	vi.useFakeTimers();
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
		let set: ReturnType<typeof vi.fn> | undefined;
		await signIn(async () => {
			const { lang } = await import('./lang.svelte');
			set = vi.spyOn(lang, 'set') as unknown as ReturnType<typeof vi.fn>;
		});
		expect(set).not.toHaveBeenCalled();
		window.history.replaceState(null, '', '/');
	});

	it('adopts a saved account theme', async () => {
		localStorage.setItem('theme', 'dark');
		profile = { email: 'r@example.com', theme: 'sepia', font_scale: 1, tts_rate: 1 };
		const theme = await signIn();
		expect(theme.preference).toBe('sepia');
	});
});
