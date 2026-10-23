import { describe, expect, it, vi } from 'vitest';

/**
 * The Supabase client as the phone app builds it: sign-in on, the session in
 * the phone's own store, and no session read from the URL (nothing ever lands
 * back on the app's capacitor:// page).
 */
const storage = vi.hoisted(() => ({ getItem: vi.fn(), setItem: vi.fn(), removeItem: vi.fn() }));
vi.mock('./platform', () => ({ IS_APP: true, authStorage: storage }));
vi.mock('$env/dynamic/public', () => ({
	PUBLIC_API_BASE_URL: '',
	env: { PUBLIC_SUPABASE_URL: 'https://ref.supabase.co', PUBLIC_SUPABASE_ANON_KEY: 'anon' }
}));
const createClient = vi.hoisted(() => vi.fn(() => ({ auth: {} })));
vi.mock('@supabase/supabase-js', () => ({ createClient }));

const { authEnabled, supabase } = await import('./supabase');

describe('supabase in the app', () => {
	it('is enabled, keeps the session in the phone’s store, and reads no URL', async () => {
		expect(authEnabled).toBe(true);
		await supabase();
		expect(createClient).toHaveBeenCalledWith('https://ref.supabase.co', 'anon', {
			auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: false, storage }
		});
	});
});
