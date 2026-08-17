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
		trace: 'on-first-retry'
	},
	projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
	webServer: [
		{
			// Serves the adapter-static output, including the 200.html SPA fallback.
			command: `npm run preview -- --port ${PORT} --strictPort`,
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
