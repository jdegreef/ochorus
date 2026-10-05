import { describe, expect, it, vi } from 'vitest';

/**
 * The era page's hreflang names only the locales whose shelf has a writer in
 * the era (the rest are an empty, noindexed state) — and falls back to every
 * locale, not to none, when the API can't say.
 */
vi.mock('$lib/lang.svelte', () => ({ getLang: () => 'en' }));
const presence = vi.hoisted(() => vi.fn());
vi.mock('$lib/library-public', () => ({
	listAuthors: async () => [],
	listBooks: async () => [],
	listEraPresence: presence
}));

const { load } = await import('./[era]/+page');
const run = (era: string) =>
	(load as unknown as (e: { params: { era: string }; fetch: typeof fetch }) => Promise<{
		eraLocales: string[] | null;
	}>)({ params: { era }, fetch: globalThis.fetch });

describe('era load', () => {
	it('lists the locales with a writer born in the era', async () => {
		// 1600 is a Puritan; null is undated (filed under modern).
		presence.mockResolvedValue({ en: [1600, null], es: [null], sw: [1600] });
		expect((await run('puritans')).eraLocales).toEqual(['en', 'sw']);
		expect((await run('modern')).eraLocales).toEqual(['en', 'es']);
	});

	it('redirects the retired contemporary era to modern', async () => {
		await expect(run('contemporary')).rejects.toMatchObject({
			status: 308,
			location: '/biographies/era/modern/'
		});
	});

	it('is null when the endpoint is unavailable, so the page keeps every locale', async () => {
		presence.mockRejectedValue(new Error('404'));
		expect((await run('puritans')).eraLocales).toBeNull();
	});
});
