/**
 * What a SERIES share card is drawn from, read straight off the content
 * fixture — shared by `generate-series-og.mjs` (which draws the cards) and
 * `src/lib/seriesCards.test.ts` (which recomputes the digests to catch a stale
 * card), so the two cannot disagree about what "the content" is.
 *
 * English only, like every other card set: the series row's own English
 * title, tagline and description, and its published English volumes in order
 * (slug, position, cover). Each book file is read only up to the end of its
 * first row — the book itself; its chapters, ~139 MB across the English
 * library, are never parsed.
 */
import { createHash } from 'node:crypto';
import { closeSync, openSync, readFileSync, readSync, readdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const CONTENT = resolve(HERE, '../../backend/library/fixtures/content');
export const STATIC = resolve(HERE, '../static');

/** @typedef {{ slug: string, position: number | null, cover: string }} Volume */
/** @typedef {{ title: string, tagline: string, description: string, books: Volume[] }} SeriesCard */

/** The first row of a fixture file (the book), without reading the rest.
 *  @param {string} path */
function firstRow(path) {
	const fd = openSync(path, 'r');
	try {
		let text = '';
		const buf = Buffer.alloc(1 << 16);
		for (let pos = 0; ; ) {
			const n = readSync(fd, buf, 0, buf.length, pos);
			text += buf.toString('utf8', 0, n);
			pos += n;
			const end = text.indexOf('\n},\n{');
			if (end !== -1) return JSON.parse(text.slice(text.indexOf('{'), end + 2));
			if (n === 0) return JSON.parse(text)[0];
		}
	} finally {
		closeSync(fd);
	}
}

/** slug → its card's content, for every series with at least one published
 *  English volume.
 *  @returns {Record<string, SeriesCard>} */
export function seriesCards() {
	const rows = JSON.parse(readFileSync(resolve(CONTENT, 'series.json'), 'utf8'));
	/** @type {Record<string, Volume[]>} */
	const books = {};
	for (const f of readdirSync(resolve(CONTENT, 'books'))) {
		if (!f.endsWith('.en.json')) continue;
		const { fields } = firstRow(resolve(CONTENT, 'books', f));
		const series = fields.series?.[0];
		if (!series || !fields.is_published) continue;
		(books[series] ??= []).push({
			slug: fields.slug,
			position: fields.series_position ?? null,
			cover: fields.cover_url || ''
		});
	}
	/** @type {Record<string, SeriesCard>} */
	const cards = {};
	for (const { model, fields } of rows) {
		if (model !== 'library.series' || !books[fields.slug]) continue;
		cards[fields.slug] = {
			title: fields.title,
			tagline: fields.tagline || '',
			description: fields.description || '',
			books: books[fields.slug].sort(
				(a, b) => (a.position ?? 1e9) - (b.position ?? 1e9) || a.slug.localeCompare(b.slug)
			)
		};
	}
	return cards;
}

/** The covers a card shows: the first three volumes that have one on disk.
 *  @param {SeriesCard} card */
export const coversOf = (card) => card.books.filter((b) => b.cover.startsWith('/covers/')).slice(0, 3);

/** @param {string | Buffer} s */
const sha = (s) => createHash('sha256').update(s).digest('hex');

/** Everything a card's pixels depend on that is content: the strings, the
 *  volume count, and the bytes of the covers it shows.
 *  @param {SeriesCard} card */
export function contentDigest(card) {
	return sha(
		[
			card.title,
			card.tagline,
			card.description,
			String(card.books.length),
			...coversOf(card).map((b) => `${b.cover}:${sha(readFileSync(resolve(STATIC, b.cover.slice(1))))}`)
		].join('\0')
	);
}

/** The drawing code, as bytes. */
export const compositionDigest = () =>
	sha(
		['generate-series-og.mjs', 'series-og-content.mjs', 'og-card.mjs']
			.map((f) => readFileSync(resolve(HERE, f), 'utf8'))
			.join('\0')
	);
