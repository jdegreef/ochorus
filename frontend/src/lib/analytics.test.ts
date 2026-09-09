import { beforeEach, describe, expect, it, vi } from 'vitest';

function plausibleScripts(): HTMLScriptElement[] {
	return [...document.querySelectorAll('script[data-domain]')] as HTMLScriptElement[];
}

/**
 * Load a fresh analytics module with the given public env applied. analytics.ts
 * reads env at module-eval, so we resetModules first — then mutate the SAME
 * post-reset `env` instance the re-imported module will see. Mutating the
 * top-level import instead would miss: resetModules gives analytics a new,
 * empty env-public stand-in. (Mirrors listen.finish.test.ts, which re-stubs its
 * globals after resetModules for the same reason.)
 */
async function loadAnalytics(publicEnv: Record<string, string> = {}) {
	vi.resetModules();
	const { env } = await import('$env/dynamic/public');
	Object.assign(env, publicEnv);
	return import('./analytics');
}

describe('analytics (Plausible)', () => {
	beforeEach(() => {
		for (const s of plausibleScripts()) s.remove();
	});

	it('is disabled and injects nothing when no domain is configured', async () => {
		const { ANALYTICS_ENABLED, initAnalytics } = await loadAnalytics();
		expect(ANALYTICS_ENABLED).toBe(false);
		initAnalytics();
		expect(plausibleScripts()).toHaveLength(0);
	});

	it('injects the Cloud script with the configured data-domain', async () => {
		const { ANALYTICS_ENABLED, initAnalytics } = await loadAnalytics({
			PUBLIC_PLAUSIBLE_DOMAIN: 'ochorus.com'
		});
		expect(ANALYTICS_ENABLED).toBe(true);
		initAnalytics();
		const scripts = plausibleScripts();
		expect(scripts).toHaveLength(1);
		expect(scripts[0].getAttribute('data-domain')).toBe('ochorus.com');
		expect(scripts[0].src).toBe('https://plausible.io/js/script.js');
		expect(scripts[0].defer).toBe(true);
	});

	it('honours a self-hosted script override', async () => {
		const { initAnalytics } = await loadAnalytics({
			PUBLIC_PLAUSIBLE_DOMAIN: 'ochorus.com',
			PUBLIC_PLAUSIBLE_SRC: 'https://stats.ochorus.com/js/script.js'
		});
		initAnalytics();
		expect(plausibleScripts()[0].src).toBe('https://stats.ochorus.com/js/script.js');
	});

	it('injects at most once across repeated calls', async () => {
		const { initAnalytics } = await loadAnalytics({ PUBLIC_PLAUSIBLE_DOMAIN: 'ochorus.com' });
		initAnalytics();
		initAnalytics();
		initAnalytics();
		expect(plausibleScripts()).toHaveLength(1);
	});
});
