import { describe, expect, it, vi } from 'vitest';

/** Google One Tap never runs in the phone app, even with a client ID set. */
vi.mock('$lib/platform', () => ({ IS_APP: true }));
vi.mock('$env/dynamic/public', () => ({
	PUBLIC_API_BASE_URL: '',
	env: { PUBLIC_GOOGLE_CLIENT_ID: 'test-client.apps.googleusercontent.com' }
}));
vi.mock('$lib/auth.svelte', () => ({ auth: {} }));

const { ONE_TAP_ENABLED } = await import('./oneTap');

describe('One Tap in the app', () => {
	it('is off', () => {
		expect(ONE_TAP_ENABLED).toBe(false);
	});
});
