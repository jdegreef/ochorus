#!/usr/bin/env node
/**
 * Tell IndexNow (Bing, Yandex, Seznam, Naver…) which pages changed recently.
 *
 * Google ignores IndexNow and learns about changes from the sitemap's
 * <lastmod>. Bing does not wait: a submitted URL is usually crawled within
 * hours rather than weeks, and Bing's index is also what ChatGPT search and
 * Copilot read. The cost is one POST a day.
 *
 * WHAT IS SENT. Every URL in the live sitemap that is new or whose <lastmod>
 * moved since the last run, which is remembered in `--state` (a JSON map of
 * URL → lastmod; the workflow keeps it in the Actions cache). Comparing with
 * what we last SAW, not with the calendar, is the point: <lastmod> is when the
 * content changed, and the page can reach the live sitemap days later (a
 * backend-only change waits for the next web build), so a "changed in the last
 * day" window would drop it for good.
 *
 * With no state yet (the first run, or an evicted cache) it falls back to URLs
 * whose <lastmod> is within `--since` days (default 1). A URL with no <lastmod>
 * is only sent when it is NEW: otherwise we don't know it changed, and
 * IndexNow asks for changed URLs only.
 *
 * The sitemap is the one list of pages we already promise are real, built and
 * indexable (prerenderCoverage.test.ts), so this never submits a shell or a
 * noindexed page.
 *
 * WHY THE LIVE SITEMAP, NOT THE BUILD. Like check-content-prerendered.mjs this
 * is about what a deploy PRODUCED, so it reads the deployed site. It runs on a
 * schedule (.github/workflows/indexnow.yml) rather than on push, because main
 * auto-deploys and a push-triggered run would read the sitemap before Render
 * had shipped it.
 *
 * THE KEY is public by design: IndexNow proves you own the host by fetching
 * `<host>/<key>.txt` and checking it holds the key. It lives in
 * static/<key>.txt; rotating it is a new file plus a new KEY below.
 *
 *   node scripts/indexnow.mjs --state indexnow-state.json   # what changed since last run
 *   node scripts/indexnow.mjs --since 7       # no state: the last week
 *   node scripts/indexnow.mjs --dry-run       # list what would be sent, send nothing
 *   node scripts/indexnow.mjs --base https://staging.example
 *
 * Only node builtins and global fetch — nothing to install.
 */

import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

export const KEY = '67db54cf8e5fc6b47fd5d4ab4ef3a3ab';
export const ENDPOINT = 'https://api.indexnow.org/indexnow';
/** The protocol's per-request ceiling. */
export const BATCH = 10000;

/** @param {string} s */
const unescape = (s) =>
	s
		.replace(/&lt;/g, '<')
		.replace(/&gt;/g, '>')
		.replace(/&quot;/g, '"')
		.replace(/&apos;/g, "'")
		.replace(/&amp;/g, '&');

/**
 * `<loc>`s of a `<sitemapindex>` — the child sitemaps.
 * @param {string} xml
 * @returns {string[]}
 */
export function childSitemaps(xml) {
	return [...xml.matchAll(/<sitemap>\s*<loc>([^<]+)<\/loc>/g)].map((m) => unescape(m[1].trim()));
}

/**
 * `{ loc, lastmod }` for each `<url>` of a `<urlset>`. Parsed by block so an
 * `xhtml:link` alternate or an `image:loc` is never mistaken for the page.
 * @param {string} xml
 * @returns {{ loc: string, lastmod: string | null }[]}
 */
export function urlEntries(xml) {
	return [...xml.matchAll(/<url>([\s\S]*?)<\/url>/g)].map(([, block]) => ({
		loc: unescape(block.match(/<loc>([^<]+)<\/loc>/)?.[1].trim() ?? ''),
		lastmod: block.match(/<lastmod>([^<]+)<\/lastmod>/)?.[1].trim() ?? null
	}));
}

/**
 * The `YYYY-MM-DD` (UTC) `days` before `now`.
 * @param {Date} now
 * @param {number} days
 */
export const cutoff = (now, days) =>
	new Date(now.getTime() - days * 86_400_000).toISOString().slice(0, 10);

/**
 * The URLs whose lastmod is on or after `since` (a `YYYY-MM-DD`), deduped.
 * @param {{ loc: string, lastmod: string | null }[]} entries
 * @param {string} since
 * @returns {string[]}
 */
export function changedSince(entries, since) {
	/** @type {Set<string>} */
	const out = new Set();
	for (const e of entries) if (e.loc && e.lastmod && e.lastmod.slice(0, 10) >= since) out.add(e.loc);
	return [...out];
}

/**
 * The URLs that are new or whose lastmod moved since `previous` (URL → lastmod
 * at the last run), deduped.
 * @param {{ loc: string, lastmod: string | null }[]} entries
 * @param {Record<string, string | null>} previous
 * @returns {string[]}
 */
export function changedFrom(entries, previous) {
	/** @type {Set<string>} */
	const out = new Set();
	for (const e of entries) {
		if (!e.loc) continue;
		if (!(e.loc in previous) || (e.lastmod && e.lastmod !== previous[e.loc])) out.add(e.loc);
	}
	return [...out];
}

/**
 * What to remember for next time: URL → lastmod.
 * @param {{ loc: string, lastmod: string | null }[]} entries
 * @returns {Record<string, string | null>}
 */
export const snapshot = (entries) =>
	Object.fromEntries(entries.filter((e) => e.loc).map((e) => [e.loc, e.lastmod]));

/**
 * The IndexNow request bodies for `urls` on `base`.
 * @param {string} base
 * @param {string[]} urls
 */
export function payloads(base, urls) {
	const host = new URL(base).host;
	const bodies = [];
	for (let i = 0; i < urls.length; i += BATCH) {
		bodies.push({
			host,
			key: KEY,
			keyLocation: `${base}/${KEY}.txt`,
			urlList: urls.slice(i, i + BATCH)
		});
	}
	return bodies;
}

/** @param {string} url */
async function text(url) {
	const res = await fetch(url);
	if (!res.ok) throw new Error(`${url} → HTTP ${res.status}`);
	return res.text();
}

async function main() {
	const args = process.argv.slice(2);
	/** @type {(name: string, fallback: string) => string} */
	const opt = (name, fallback) => {
		const i = args.indexOf(`--${name}`);
		return i !== -1 && args[i + 1] ? args[i + 1] : fallback;
	};
	const base = opt('base', 'https://ochorus.com').replace(/\/$/, '');
	const days = Number(opt('since', '1'));
	if (!Number.isFinite(days) || days < 0) throw new Error(`--since must be a number of days, got ${opt('since', '')}`);
	const dryRun = args.includes('--dry-run');
	const statePath = opt('state', '');

	// The key file must be live before IndexNow will accept anything — check it
	// here so a missing file reads as that, not as an opaque 403 from the API.
	const served = (await text(`${base}/${KEY}.txt`)).trim();
	if (served !== KEY) throw new Error(`${base}/${KEY}.txt does not hold the key (got ${JSON.stringify(served.slice(0, 40))})`);

	const children = childSitemaps(await text(`${base}/sitemap.xml`));
	// An empty index would make every run a silent "nothing changed".
	if (!children.length) throw new Error(`${base}/sitemap.xml lists no child sitemaps`);
	const entries = (await Promise.all(children.map(async (c) => urlEntries(await text(c))))).flat();
	/** @type {Record<string, string | null> | null} */
	const previous =
		statePath && existsSync(statePath) ? JSON.parse(readFileSync(statePath, 'utf8')) : null;
	const since = cutoff(new Date(), days);
	const urls = previous ? changedFrom(entries, previous) : changedSince(entries, since);
	console.log(
		`${entries.length} sitemap URLs; ${urls.length} changed ` +
			(previous ? 'since the last run.' : `since ${since} (no previous state).`)
	);
	if (dryRun) {
		for (const u of urls) console.log(`  ${u}`);
		return;
	}
	for (const body of payloads(base, urls)) {
		const res = await fetch(ENDPOINT, {
			method: 'POST',
			headers: { 'content-type': 'application/json; charset=utf-8' },
			body: JSON.stringify(body)
		});
		// 200 and 202 both mean accepted (202: key validation pending).
		if (res.status !== 200 && res.status !== 202) {
			throw new Error(`IndexNow rejected ${body.urlList.length} URLs: HTTP ${res.status} ${await res.text()}`);
		}
		console.log(`Submitted ${body.urlList.length} URLs (HTTP ${res.status}).`);
	}
	// Only after every batch was accepted: a failed run keeps the old state, so
	// the next one retries what this one could not send.
	if (statePath) writeFileSync(statePath, JSON.stringify(snapshot(entries)));
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
	main().catch((e) => {
		console.error(`✗ ${e instanceof Error ? e.message : e}`);
		process.exit(1);
	});
}
