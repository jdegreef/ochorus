import { describe, expect, it } from 'vitest';
import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import {
	BATCH,
	KEY,
	changedFrom,
	changedSince,
	childSitemaps,
	cutoff,
	payloads,
	snapshot,
	urlEntries
} from '../../scripts/indexnow.mjs';
import { urlsetXml, type Entry } from './sitemap';

describe('indexnow', () => {
	it('ships the key file IndexNow verifies ownership against', () => {
		// Resolved from cwd (vitest runs in frontend/), as prerenderCoverage does.
		const file = resolve(process.cwd(), 'static', `${KEY}.txt`);
		expect(existsSync(file)).toBe(true);
		expect(readFileSync(file, 'utf8').trim()).toBe(KEY);
	});

	it('reads the child sitemaps of an index', () => {
		const xml =
			'<sitemapindex><sitemap><loc>https://ochorus.com/sitemap-books.xml</loc></sitemap>' +
			'<sitemap>\n  <loc>https://ochorus.com/sitemap-pages.xml</loc>\n</sitemap></sitemapindex>';
		expect(childSitemaps(xml)).toEqual([
			'https://ochorus.com/sitemap-books.xml',
			'https://ochorus.com/sitemap-pages.xml'
		]);
	});

	it('parses what the sitemap module actually emits, alternates and images aside', () => {
		const entry: Entry = {
			byLocale: new Map([
				['en', '/books/humility/'],
				['sw', '/books/humility/']
			]),
			lastmod: '2026-09-28T10:00:00Z',
			images: new Map([['en', 'https://ochorus.com/covers/humility.png']])
		};
		const undated: Entry = { byLocale: new Map([['en', '/about']]) };
		const rows = urlEntries(urlsetXml([entry, undated]));
		expect(rows.map((r) => r.loc)).toEqual([
			expect.stringMatching(/\/books\/humility\/$/),
			expect.stringMatching(/\/sw\/books\/humility\/$/),
			expect.stringMatching(/\/about$/)
		]);
		expect(rows.map((r) => r.lastmod)).toEqual(['2026-09-28', '2026-09-28', null]);
	});

	it('sends only dated URLs changed on or after the cutoff, once each', () => {
		const since = cutoff(new Date('2026-09-29T06:00:00Z'), 1);
		expect(since).toBe('2026-09-28');
		const urls = changedSince(
			[
				{ loc: 'a', lastmod: '2026-09-29' },
				{ loc: 'b', lastmod: '2026-09-28' },
				{ loc: 'b', lastmod: '2026-09-28' },
				{ loc: 'c', lastmod: '2026-09-27' },
				{ loc: 'd', lastmod: null }
			],
			since
		);
		expect(urls).toEqual(['a', 'b']);
	});

	it('sends what is new or re-dated since the last run, however old its lastmod', () => {
		// The case a calendar window misses: content changed on the 20th but only
		// reached the live sitemap now.
		const previous = { a: '2026-09-01', b: '2026-09-01', c: null };
		const entries = [
			{ loc: 'a', lastmod: '2026-09-01' },
			{ loc: 'b', lastmod: '2026-09-20' },
			{ loc: 'c', lastmod: null },
			{ loc: 'd', lastmod: null },
			{ loc: 'e', lastmod: '2026-08-01' }
		];
		expect(changedFrom(entries, previous)).toEqual(['b', 'd', 'e']);
		expect(changedFrom(entries, snapshot(entries))).toEqual([]);
	});

	it('batches at the protocol ceiling and points at the key file', () => {
		const urls = Array.from({ length: BATCH + 1 }, (_, i) => `https://ochorus.com/p${i}`);
		const bodies = payloads('https://ochorus.com', urls);
		expect(bodies.map((b) => b.urlList.length)).toEqual([BATCH, 1]);
		expect(bodies[0]).toMatchObject({
			host: 'ochorus.com',
			key: KEY,
			keyLocation: `https://ochorus.com/${KEY}.txt`
		});
	});
});
