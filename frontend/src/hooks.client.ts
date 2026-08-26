import type { HandleClientError } from '@sveltejs/kit';
import { env } from '$env/dynamic/public';

/**
 * Opt-in error monitoring: does nothing until PUBLIC_SENTRY_DSN is set, so local
 * dev and unconfigured deploys are unaffected. Errors-only by default.
 *
 * Loaded dynamically. `init` and `handleErrorWithSentry` were imported at the
 * top of this file, and this file is part of the client ENTRY — so the whole
 * Sentry browser SDK shipped to every reader on every page even when no DSN was
 * configured and it could do nothing at all. The `if (env.PUBLIC_SENTRY_DSN)`
 * guard was a runtime guard on a static import; it never gated the download.
 */

type SentryModule = typeof import('@sentry/sveltekit');

let sentry: Promise<SentryModule> | null = null;

function loadSentry(): Promise<SentryModule> {
	if (!sentry) {
		sentry = import('@sentry/sveltekit').then((module) => {
			module.init({
				dsn: env.PUBLIC_SENTRY_DSN,
				environment: env.PUBLIC_SENTRY_ENVIRONMENT || 'production',
				// WHICH build an error came from. Without it every browser report
				// is attributed to one undifferentiated "production", so a
				// regression cannot be traced to the deploy that introduced it.
				// Baked in at build time (see vite.config.ts); empty outside a
				// Render build, and an empty release is worse than none — Sentry
				// would group every local and CI error under "".
				release: __RELEASE__ || undefined,
				tracesSampleRate: 0
			});
			return module;
		});
	}
	return sentry;
}

// Start loading as soon as the app boots when monitoring is on, so the SDK is
// ready before the first error rather than being fetched during one — but
// off the critical path, since nothing awaits this.
if (env.PUBLIC_SENTRY_DSN) void loadSentry();

// Report any uncaught load/render error (to Sentry when configured) and always
// leave a console trace for local debugging. The returned shape is what the
// root +error.svelte renders.
const report: HandleClientError = ({ error, event }) => {
	console.error('[ochorus] client error at', event.url.pathname, error);
	return { message: 'Something went wrong loading this page.' };
};

export const handleError: HandleClientError = async (input) => {
	// Without a DSN there is nothing to send and nothing to load: report and
	// return, exactly as before, without ever touching the SDK.
	if (!env.PUBLIC_SENTRY_DSN) return report(input);
	try {
		const { handleErrorWithSentry } = await loadSentry();
		return handleErrorWithSentry(report)(input);
	} catch {
		// The SDK failed to load. An error handler that throws while handling an
		// error is the one thing it must never do, so fall back to reporting.
		return report(input);
	}
};
