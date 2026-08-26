import { afterEach, describe, expect, it, vi } from 'vitest';
import { getSermon, getPlan, getBook } from './library-public';

/**
 * The localized() English-fallback contract: a detail fetch for a language the
 * work doesn't have (a 404) degrades to the English original instead of
 * throwing, so a shared /lg/... link or a mid-read language switch reads rather
 * than dead-ending at the not-found page. getBook already did this; these pin
 * that getSermon and getPlan now do too (P2 review item #14).
 */

function mockFetchByLanguage(present: string[], payload: unknown) {
	return vi.fn(async (url: string | URL) => {
		const lang = new URL(String(url), 'http://x').searchParams.get('language');
		if (lang && present.includes(lang)) {
			return new Response(JSON.stringify(payload), {
				status: 200,
				headers: { 'content-type': 'application/json' }
			});
		}
		return new Response('{"detail":"Not found."}', {
			status: 404,
			headers: { 'content-type': 'application/json' }
		});
	});
}

afterEach(() => vi.restoreAllMocks());

/**
 * Payloads carrying what the guards require (see $lib/payloadGuards).
 *
 * These were previously `{ slug, title }` — enough for a fallback assertion, and
 * nothing like what the API sends. The guards rejected them the moment they
 * landed, which is the guards working: a double that does not resemble the real
 * thing cannot catch the day the real thing changes.
 */
const sermonPayload = (title: string) => ({
	slug: 's',
	language: 'en',
	title,
	body_html: '<p>Prose.</p>',
	author_name: 'A. B. Simpson'
});
const bookPayload = (title: string) => ({ slug: 'b', language: 'en', title, chapters: [] });

describe('localized detail fallback', () => {
	it('getSermon falls back to English when the language has no row', async () => {
		const fetchSpy = mockFetchByLanguage(['en'], sermonPayload('English Sermon'));
		vi.stubGlobal('fetch', fetchSpy);
		const sermon = await getSermon('s', 'es');
		expect((sermon as { title: string }).title).toBe('English Sermon');
		// It tried es first, then fell back to en.
		const langs = fetchSpy.mock.calls.map(
			([u]) => new URL(String(u), 'http://x').searchParams.get('language')
		);
		expect(langs).toEqual(['es', 'en']);
	});

	it('getPlan falls back to English when the language has no row', async () => {
		vi.stubGlobal('fetch', mockFetchByLanguage(['en'], { slug: 'p', title: 'English Plan' }));
		const plan = await getPlan('p', 'lg');
		expect((plan as { title: string }).title).toBe('English Plan');
	});

	it('does not fall back when the requested language exists', async () => {
		const fetchSpy = mockFetchByLanguage(['en', 'lg'], sermonPayload('Luganda Sermon'));
		vi.stubGlobal('fetch', fetchSpy);
		const sermon = await getSermon('s', 'lg');
		expect((sermon as { title: string }).title).toBe('Luganda Sermon');
		expect(fetchSpy).toHaveBeenCalledTimes(1); // no fallback fetch
	});

	it('getBook keeps its existing fallback (regression guard)', async () => {
		vi.stubGlobal('fetch', mockFetchByLanguage(['en'], bookPayload('English Book')));
		const book = await getBook('b', 'sw');
		expect((book as { title: string }).title).toBe('English Book');
	});
});
