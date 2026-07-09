import type { HandleClientError } from '@sveltejs/kit';
import { env } from '$env/dynamic/public';
import { handleErrorWithSentry, init } from '@sentry/sveltekit';

// Opt-in error monitoring: does nothing until PUBLIC_SENTRY_DSN is set, so local
// dev and unconfigured deploys are unaffected. Errors-only by default.
if (env.PUBLIC_SENTRY_DSN) {
	init({
		dsn: env.PUBLIC_SENTRY_DSN,
		environment: env.PUBLIC_SENTRY_ENVIRONMENT || 'production',
		tracesSampleRate: 0
	});
}

// Report any uncaught load/render error (to Sentry when configured) and always
// leave a console trace for local debugging. The returned shape is what the
// root +error.svelte renders.
const report: HandleClientError = ({ error, event }) => {
	console.error('[ochorus] client error at', event.url.pathname, error);
	return { message: 'Something went wrong loading this page.' };
};

export const handleError = handleErrorWithSentry(report);
