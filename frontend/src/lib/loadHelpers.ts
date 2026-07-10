import { error } from '@sveltejs/kit';
import { ApiError } from './api';

/**
 * Run a page loader, translating an API 404 into a SvelteKit 404 so the
 * designed not-found page (+error.svelte) renders instead of a generic 500.
 * Any other error propagates unchanged (still a 500).
 *
 * Detail pages are prerendered from a build-time slug list of real content, so
 * this 404 branch only fires at runtime for an unknown or unpublished slug.
 */
export async function orNotFound<T>(fn: () => Promise<T>): Promise<T> {
	try {
		return await fn();
	} catch (e) {
		if (e instanceof ApiError && e.status === 404) throw error(404, 'Not found');
		throw e;
	}
}
