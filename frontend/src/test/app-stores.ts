import { readable } from 'svelte/store';

/**
 * `$app/stores` for unit tests (vitest.config.ts aliases it here): a `page`
 * at the site root. A test that needs another URL mocks the module with its
 * own `page`; this only has to exist so the import resolves.
 */
export const page = readable({
	url: new URL('https://ochorus.test/'),
	params: {} as Record<string, string>,
	route: { id: null as string | null },
	data: {} as Record<string, unknown>
});
export const navigating = readable(null);
export const updated = { subscribe: readable(false).subscribe, check: async () => false };
