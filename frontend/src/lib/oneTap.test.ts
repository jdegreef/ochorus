import { createHash } from 'node:crypto';
import { afterEach, describe, expect, it, vi } from 'vitest';

/**
 * Google One Tap: where it asks, the nonce handshake, and that a tap becomes a
 * Supabase sign-in credited to `one_tap`.
 */
// Static and dynamic public env share one test module (vitest.config.ts), so
// the static API base the api module reads has to be here too.
vi.mock('$env/dynamic/public', () => ({
	PUBLIC_API_BASE_URL: '',
	env: { PUBLIC_GOOGLE_CLIENT_ID: 'test-client.apps.googleusercontent.com' }
}));
const auth = vi.hoisted(() => ({ signInWithGoogleIdToken: vi.fn().mockResolvedValue(null) }));
vi.mock('$lib/auth.svelte', () => ({ auth }));

const { ONE_TAP_ENABLED, makeNonce, oneTapAllowedOn, promptOneTap, signInWithCredential } =
	await import('./oneTap');
const { noteSignupSource, signupSource } = await import('./signupSource');
const { signInSheet } = await import('./signInSheet.svelte');

const sha256 = (s: string) => createHash('sha256').update(s).digest('hex');

afterEach(() => {
	localStorage.clear();
	auth.signInWithGoogleIdToken.mockReset().mockResolvedValue(null);
	signInSheet.open = false;
});
const tick = () => new Promise((r) => setTimeout(r, 0));

describe('oneTap', () => {
	it('is on when the deploy has a client ID', () => {
		expect(ONE_TAP_ENABLED).toBe(true);
	});

	it('asks on reading pages, not where a page already asks or would be intruded on', () => {
		for (const p of ['/', '/books/humility/', '/fr/books/humility/1/', '/login-help', '/articles/'])
			expect(oneTapAllowedOn(p), p).toBe(true);
		for (const p of ['/login', '/fr/login', '/reset-password', '/welcome', '/admin', '/admin/books', '/email/preferences/x'])
			expect(oneTapAllowedOn(p), p).toBe(false);
	});

	it('stays quiet for young readers', () => {
		for (const p of ['/young-readers/', '/teens/', '/fr/teens/', '/books/humility-children/', '/books/humility-teens/3/', '/es/books/humility-children/'])
			expect(oneTapAllowedOn(p), p).toBe(false);
		// A slug that merely contains the word is an ordinary book.
		expect(oneTapAllowedOn('/books/children-of-the-kingdom/')).toBe(true);
	});

	it('gives Google the SHA-256 of a fresh nonce', async () => {
		const a = await makeNonce();
		const b = await makeNonce();
		expect(a.hashed).toBe(sha256(a.raw));
		expect(a.hashed).toMatch(/^[0-9a-f]{64}$/);
		expect(a.raw).not.toBe(b.raw);
	});

	it('signs in with the credential and the RAW nonce, credited to one_tap', async () => {
		await signInWithCredential('id-token', 'raw-nonce');
		expect(auth.signInWithGoogleIdToken).toHaveBeenCalledWith('id-token', 'raw-nonce');
		expect(signupSource()).toBe('one_tap');
		expect(signInSheet.open).toBe(false);
	});

	it('on a failed exchange, puts the earlier credit back and opens the sign-up panel', async () => {
		noteSignupSource('chapter_end');
		auth.signInWithGoogleIdToken.mockResolvedValue('bad_jwt');
		expect(await signInWithCredential('id-token', 'raw-nonce')).toBe('bad_jwt');
		expect(signupSource()).toBe('chapter_end');
		expect(signInSheet.open).toBe(true);
	});

	it('leaves no credit behind when there was none before a failed exchange', async () => {
		auth.signInWithGoogleIdToken.mockResolvedValue('bad_jwt');
		await signInWithCredential('id-token', 'raw-nonce');
		expect(signupSource()).toBeNull();
	});

	it('loads Google once, prompts with the hashed nonce, and signs in on a tap', async () => {
		const id = { initialize: vi.fn(), prompt: vi.fn(), cancel: vi.fn() };
		const asking = promptOneTap('fr');
		const script = document.head.querySelector<HTMLScriptElement>(
			'script[src^="https://accounts.google.com/gsi/client"]'
		)!;
		expect(script.src).toContain('hl=fr');
		(window as unknown as { google: unknown }).google = { accounts: { id } };
		script.onload!(new Event('load'));
		await asking;

		expect(id.prompt).toHaveBeenCalledTimes(1);
		const config = id.initialize.mock.calls[0][0];
		expect(config.client_id).toBe('test-client.apps.googleusercontent.com');
		expect(config.use_fedcm_for_prompt).toBe(true);
		expect(config.nonce).toMatch(/^[0-9a-f]{64}$/);

		config.callback({ credential: 'id-token' });
		await tick();
		const [token, raw] = auth.signInWithGoogleIdToken.mock.calls[0];
		expect(token).toBe('id-token');
		expect(sha256(raw)).toBe(config.nonce);

		// Once per page load.
		await promptOneTap('fr');
		expect(id.prompt).toHaveBeenCalledTimes(1);
	});
});
