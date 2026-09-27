import { describe, expect, it, vi } from 'vitest';

import { CHAPTER_BATCH_SIZE, createChapterBatcher } from './chapterBatch';
import { chapterApiPath } from './library-public';

const API = 'https://api.example.org';
// The exact URL getChapterWithLang sends — built with its own path helper, so a
// change there that the batcher doesn't recognise fails here.
const chapterUrl = (slug: string, order: number, query = 'language=en') => {
	const url = new URL(`${API}${chapterApiPath(slug, order, 'en')}`);
	url.search = query;
	return url.toString();
};

const json = (body: unknown, status = 200) =>
	new Response(JSON.stringify(body), {
		status,
		headers: { 'Content-Type': 'application/json' }
	});

/** A fake batch endpoint serving `total` chapters, recording each request. */
function batchApi(total: number, status = 200) {
	return vi.fn(async (input: RequestInfo | URL) => {
		const url = new URL(String(input), API);
		const from = Number(url.searchParams.get('from'));
		const limit = Number(url.searchParams.get('limit'));
		const chapters = [];
		for (let o = from; o < Math.min(from + limit, total + 1); o++) {
			chapters.push({
				order: o,
				title: `Ch ${o}`,
				lang: url.searchParams.get('language')
			});
		}
		return status === 200 ? json(chapters) : json({ detail: 'nope' }, status);
	});
}

describe('createChapterBatcher', () => {
	it('answers every chapter of a book from one request per run', async () => {
		const fetch = batchApi(30);
		const batcher = createChapterBatcher(API);
		for (let o = 1; o <= 30; o++) {
			const res = await batcher(new Request(chapterUrl('w', o)), fetch);
			expect(res?.status).toBe(200);
			expect(await res!.json()).toEqual({
				order: o,
				title: `Ch ${o}`,
				lang: 'en'
			});
		}
		expect(fetch).toHaveBeenCalledTimes(2);
		const first = new URL(String(fetch.mock.calls[0][0]), API);
		expect(first.pathname + first.search).toBe(
			`/api/library/books/w/chapters/?language=en&from=1&limit=${CHAPTER_BATCH_SIZE}`
		);
		expect(String(fetch.mock.calls[1][0])).toContain(`from=${CHAPTER_BATCH_SIZE + 1}&`);
	});

	it('keeps languages and books in separate runs', async () => {
		const fetch = batchApi(3);
		const batcher = createChapterBatcher(API);
		const es = await batcher(new Request(chapterUrl('w', 1, 'language=es')), fetch);
		const en = await batcher(new Request(chapterUrl('w', 1)), fetch);
		const other = await batcher(new Request(chapterUrl('x', 1)), fetch);
		expect((await es!.json()).lang).toBe('es');
		expect((await en!.json()).lang).toBe('en');
		expect(other?.status).toBe(200);
		expect(fetch).toHaveBeenCalledTimes(3);
	});

	it('falls through when the batch fails, without retrying it per chapter', async () => {
		// A 404 must reach the chapter page as the API's own 404, so the English
		// fallback in localizedWithLang still sees it — falling through does that.
		const fetch = batchApi(3, 404);
		const batcher = createChapterBatcher(API);
		expect(await batcher(new Request(chapterUrl('w', 1, 'language=fr')), fetch)).toBeNull();
		expect(await batcher(new Request(chapterUrl('w', 2, 'language=fr')), fetch)).toBeNull();
		expect(fetch).toHaveBeenCalledTimes(1);

		const down = vi.fn(async () => {
			throw new Error('ECONNRESET');
		});
		expect(await createChapterBatcher(API)(new Request(chapterUrl('w', 1)), down)).toBeNull();
	});

	it('falls through for a chapter the run does not hold', async () => {
		const batcher = createChapterBatcher(API);
		expect(await batcher(new Request(chapterUrl('w', 9)), batchApi(3))).toBeNull();
	});

	it('hands each chapter over once; a repeat request goes to the API', async () => {
		const fetch = batchApi(3);
		const batcher = createChapterBatcher(API);
		expect(await batcher(new Request(chapterUrl('w', 1)), fetch)).not.toBeNull();
		expect(await batcher(new Request(chapterUrl('w', 1)), fetch)).toBeNull();
	});

	it('leaves every other request alone', async () => {
		const fetch = batchApi(3);
		const batcher = createChapterBatcher(API);
		const untouched = [
			new Request(`${API}/api/library/books/w/?language=en`),
			new Request(chapterUrl('w', 1, 'language=en&edition=modern')),
			new Request(chapterUrl('w', 1, '')),
			new Request(`https://elsewhere.example/api/library/books/w/chapters/1/?language=en`),
			new Request(chapterUrl('w', 1), { method: 'POST', body: '{}' })
		];
		for (const req of untouched) expect(await batcher(req, fetch)).toBeNull();
		expect(fetch).not.toHaveBeenCalled();
	});
});
