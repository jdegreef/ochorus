import { afterEach, describe, expect, it, vi } from 'vitest';
import { getArticle, getBook, getChapterWithLang, getSermon } from './library-public';
import { PayloadError } from './payloadGuards';

/**
 * That the guards are actually WIRED, not merely correct.
 *
 * `payloadGuards.test.ts` checks the checker. This drives the real helpers over
 * a stubbed fetch, because the failure that matters is not a wrong guard — it is
 * a guard nobody called. `getChapterWithLang` is here rather than `getChapter`
 * for exactly that reason: it is the path the chapter reader takes, and guarding
 * only its sibling would have left the reader unchecked.
 */
const respond = (payload: unknown) =>
	vi.fn(
		async () =>
			new Response(JSON.stringify(payload), {
				status: 200,
				headers: { 'content-type': 'application/json' }
			})
	);

const CHAPTER = {
	order: 3,
	title: 'The Path',
	body_html: '<p>Prose.</p>',
	book_title: 'Humility',
	book_slug: 'humility',
	author_name: 'Andrew Murray'
};

afterEach(() => vi.restoreAllMocks());

describe('the reader helpers reject a payload they cannot render', () => {
	it('a chapter whose prose field was renamed', async () => {
		const { body_html, ...renamed } = CHAPTER;
		vi.stubGlobal('fetch', respond({ ...renamed, body: body_html }));
		await expect(getChapterWithLang('humility', 3, 'en')).rejects.toThrow(PayloadError);
	});

	it('a book with no table of contents', async () => {
		vi.stubGlobal('fetch', respond({ slug: 'b', language: 'en', title: 'Humility' }));
		await expect(getBook('b', 'en')).rejects.toThrow(/chapters/);
	});

	it('a sermon with no body', async () => {
		vi.stubGlobal('fetch', respond({ slug: 's', language: 'en', title: 'Himself' }));
		await expect(getSermon('s', 'en')).rejects.toThrow(PayloadError);
	});

	it('an article with no body', async () => {
		vi.stubGlobal('fetch', respond({ slug: 'a', language: 'en', h1: 'How to Pray' }));
		await expect(getArticle('a', 'en')).rejects.toThrow(PayloadError);
	});

	it('and pass a payload they can', async () => {
		vi.stubGlobal('fetch', respond(CHAPTER));
		const { data } = await getChapterWithLang('humility', 3, 'en');
		expect(data.body_html).toBe('<p>Prose.</p>');
	});

	// The error has to say which endpoint, or a report names a symptom and not
	// a cause.
	it('names the endpoint in the message', async () => {
		vi.stubGlobal('fetch', respond({ ...CHAPTER, body_html: undefined }));
		await expect(getChapterWithLang('humility', 3, 'en')).rejects.toThrow(
			/chapter humility\/3/
		);
	});
});
