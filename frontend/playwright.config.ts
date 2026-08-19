import { defineConfig, devices } from '@playwright/test';

/**
 * Browser smoke tests against the BUILT site and a real API.
 *
 * Why this exists: every other gate is blind to the running app. `npm run check`
 * type-checks, vitest covers pure logic, and the prerender build only proves the
 * API answered at build time — nothing executes hydration, client-side routing,
 * or a live data fetch. So a renamed DRF field or a broken store could ship with
 * all of CI green (see the review's frontend/backend drift finding).
 *
 * Contract: this suite needs (a) a production build in `build/`, compiled with
 * PUBLIC_API_BASE_URL pointing at the API below, and (b) that API running with
 * seeded content. `reuseExistingServer` means CI — which already starts a seeded
 * API and builds the frontend — reuses both instead of starting its own.
 */
const API = process.env.PUBLIC_API_BASE_URL || 'http://localhost:8000';
// 4173 is not arbitrary: it's in the API's dev CORS allowlist (see
// config/settings.py). Overriding it means adding that origin there too, or every
// client fetch is blocked by preflight and surfaces as an opaque poll timeout.
const PORT = Number(process.env.E2E_PORT || 4173);

export default defineConfig({
	testDir: 'e2e',
	// The whole point is a fast signal; a smoke test that takes minutes gets skipped.
	timeout: 30_000,
	expect: { timeout: 10_000 },
	fullyParallel: true,
	forbidOnly: !!process.env.CI,
	retries: process.env.CI ? 1 : 0,
	reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',
	use: {
		baseURL: `http://localhost:${PORT}`,
		trace: 'on-first-retry',
		// Block service workers. On a fresh profile the PWA registers, takes
		// control and reloads the page (lib/pwa.svelte.ts), which lands as a second
		// document load in the middle of a test and makes any "did this navigate on
		// the client?" assertion flaky. These tests are about routing and API data;
		// offline/PWA behaviour deserves its own dedicated test rather than noise
		// inside every one of these.
		serviceWorkers: 'block'
	},
	projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
	webServer: [
		{
			// Serves `build/` the way the static host does — NOT `vite preview`,
			// which serves SvelteKit's own output and SSRs anything not prerendered,
			// so build/200.html never gets served and a missing page renders through
			// a server path production doesn't have. See scripts/serve-build.mjs.
			command: `node scripts/serve-build.mjs build ${PORT}`,
			url: `http://localhost:${PORT}/`,
			reuseExistingServer: !process.env.CI,
			timeout: 60_000
		},
		{
			// The API. In CI this is already up, so it is reused, not restarted.
			command:
				'cd ../backend && DJANGO_DEBUG=true uv run python manage.py runserver 8000 --noreload',
			url: `${API}/api/health/`,
			reuseExistingServer: true,
			timeout: 120_000
		}
	]
});
