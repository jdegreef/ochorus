#!/usr/bin/env node
/**
 * Every author and book this COMMIT ships must have a real page on the site.
 *
 * The reader is prerendered from the API at build time, and content rows reach
 * the API in its release step. When the web build enumerates content before the
 * API holds it, the page is never generated and the static host answers with the
 * noindex `200.html` shell instead. It fails silently: the deploy is green, the
 * page is "up", and only a later unrelated build produces it.
 *
 * That has now cost four corrective commits — #1138 (five early-church bios),
 * #1163 (three Schaff books), #1165 (three monastic bios) and #1173 (E. M.
 * Bounds) — and every one of them was found by a person looking at the page, not
 * by a check.
 *
 * WHY THE EXISTING GUARDS DO NOT CATCH IT. Both are self-referential:
 *
 *   * `src/lib/prerenderCoverage.test.ts` compares the sitemap to the build. The
 *     sitemap is generated from the same API the build read, so when a row is
 *     missing BOTH halves lack it, the two agree, and the guard passes having
 *     inspected nothing. (CI's own comment names this: the built-output guards
 *     "are blind to a page that was never built".)
 *   * `scripts/check-slashes.mjs` probes a deployed host, but also enumerates
 *     from the sitemap, so it inherits the same blindness.
 *
 * Nor can CI catch it: CI seeds its API from these very fixtures, so the row is
 * always present there. A build-time gate is green in exactly the case
 * production breaks.
 *
 * So this reads the EXPECTED set from the committed fixtures — the one source
 * that is not downstream of the API — and probes the deployed site for it. A
 * POST-DEPLOY probe, like check-slashes and for the same reason: the property is
 * about what the deploy produced, so it cannot be known before one happens.
 *
 *   node scripts/check-content-prerendered.mjs
 *   node scripts/check-content-prerendered.mjs --base https://staging.example
 *   node scripts/check-content-prerendered.mjs --list      # expected set, no network
 *
 * FAILS (exit 1) on a page that is missing or is a shell. The expected set
 * mirrors what the API actually publishes, so a pass is meaningful and a failure
 * is real — a guard with false positives is one people learn to ignore.
 */

import { readFileSync, readdirSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const args = process.argv.slice(2);
const opt = (name, fallback = null) => {
	const i = args.indexOf(`--${name}`);
	return i !== -1 && args[i + 1] ? args[i + 1] : fallback;
};

const BASE = opt('base', 'https://ochorus.com').replace(/\/$/, '');
// Floored at 1: `Number('x')` is NaN and `--concurrency 0` spawns no workers, so
// mapPool would leave every slot a hole, `filter` would skip them, and the audit
// would report a clean pass having made ZERO requests. A guard that passes
// vacuously is worse than no guard.
const CONCURRENCY = Math.max(1, Number(opt('concurrency', '8')) || 8);
const LIST_ONLY = args.includes('--list');

const CONTENT = fileURLToPath(
	new URL('../../backend/library/fixtures/content/', import.meta.url)
);

/** A 200 with no <title> and a tiny body is the SPA fallback shell (as check-slashes). */
const SHELL_MAX_BYTES = 8000;

const rows = (file) => JSON.parse(readFileSync(join(CONTENT, file), 'utf8'));

/**
 * The authors that get a page, mirroring `AuthorListView.get_queryset`: anyone
 * with a bio OR a book to read, imprints excluded (that page describes people,
 * and a house byline is not one). Mirroring it rather than guessing is what
 * keeps this free of false positives.
 */
function expectedAuthors(publishedAuthorSlugs) {
	const out = [];
	for (const r of rows('authors.json')) {
		if (r.model !== 'library.author') continue;
		const f = r.fields;
		if (f.is_imprint) continue;
		// `AuthorListView` counts a bio only in the requested language
		// (`own_bio = Q(original_language=lang) & …`), so an author whose bio is
		// not originally English needs an English book to appear on /authors.
		// Every fixture author is `en` today; mirroring it anyway keeps the
		// expected set correct the first time one is not.
		const lang = f.original_language || 'en';
		const hasBio =
			lang === 'en' && Boolean((f.bio || '').trim() || (f.bio_html || '').trim());
		if (hasBio || publishedAuthorSlugs.has(f.slug)) out.push(`/authors/${f.slug}/`);
	}
	return out;
}

/**
 * English books that are actually published. `is_published` is false in the
 * fixture for the six titles migration 0022 pulled for copyright, so reading it
 * here keeps those out of the expected set rather than demanding pages that are
 * correctly absent.
 */
function expectedBooks() {
	const dir = join(CONTENT, 'books');
	const urls = [];
	const authorSlugs = new Set();
	if (!existsSync(dir)) return { urls, authorSlugs };
	for (const name of readdirSync(dir).sort()) {
		if (!name.endsWith('.en.json')) continue;
		const book = rows(join('books', name)).find((r) => r.model === 'library.book');
		if (!book || book.fields.is_published === false) continue;
		urls.push(`/books/${book.fields.slug}/`);
		const author = book.fields.author;
		if (Array.isArray(author) && author[0]) authorSlugs.add(author[0]);
	}
	return { urls, authorSlugs };
}

async function probe(path) {
	const url = BASE + path;
	try {
		const res = await fetch(url, { redirect: 'follow' });
		const body = await res.text();
		return {
			path,
			status: res.status,
			bytes: Buffer.byteLength(body),
			hasTitle: /<title[^>]*>[^<]*\S[^<]*<\/title>/i.test(body)
		};
	} catch (err) {
		return { path, status: 0, bytes: 0, hasTitle: false, error: String(err) };
	}
}

/** Simple concurrency pool (as check-slashes) — this can be a few hundred URLs. */
async function mapPool(items, fn, size) {
	const out = new Array(items.length);
	let next = 0;
	await Promise.all(
		Array.from({ length: Math.min(size, items.length) }, async () => {
			while (next < items.length) {
				const i = next++;
				out[i] = await fn(items[i]);
			}
		})
	);
	return out;
}

const isShell = (r) => r.status === 200 && !r.hasTitle && r.bytes < SHELL_MAX_BYTES;

const books = expectedBooks();
const expected = [...expectedAuthors(books.authorSlugs), ...books.urls];

if (!expected.length) {
	console.error('✗ no content found in the fixtures — wrong checkout?');
	process.exit(1);
}

if (LIST_ONLY) {
	for (const p of expected) console.log(p);
	console.log(`\n${expected.length} pages expected from the fixtures`);
	process.exit(0);
}

console.log(`checking ${expected.length} fixture pages against ${BASE}\n`);
const results = await mapPool(expected, probe, CONCURRENCY);

let missing = results.filter((r) => r.status !== 200);
let shells = results.filter(isShell);
let broken = [...missing, ...shells];

// Re-probe once before declaring. main auto-deploys, so a scheduled run can land
// while Render is mid-build and see pages that are about to exist — reporting
// that as a prerender race is how a check earns a reputation for crying wolf.
// Only the failures are retried, so the cost is a pause and a handful of
// requests, and only when something already looks wrong.
if (broken.length) {
	const wait = Number(opt('retry-after', '90')) || 0;
	if (wait > 0) {
		console.error(`\n… ${broken.length} page(s) failed; re-probing in ${wait}s in case a deploy is in flight\n`);
		await new Promise((r) => setTimeout(r, wait * 1000));
		const again = await mapPool([...new Set(broken.map((r) => r.path))], probe, CONCURRENCY);
		missing = again.filter((r) => r.status !== 200);
		shells = again.filter(isShell);
		broken = [...missing, ...shells];
	}
}

for (const r of broken) {
	const why = r.status !== 200 ? `HTTP ${r.status}${r.error ? ` (${r.error})` : ''}` : 'SPA shell — no <title>';
	console.error(`✗ ${r.path.padEnd(52)} ${why}`);
}

if (!broken.length) {
	console.log(`✓ all ${expected.length} pages are prerendered and served`);
	process.exit(0);
}

// Every page failing is not 105 simultaneous prerender misses — it is the origin
// being unreachable (DNS, TLS, an outage, a blocked egress). Saying so keeps the
// alert honest: a check that cries "prerender race" at a network blip is one
// people stop believing.
if (missing.length === expected.length) {
	console.error(
		`\n✗ every one of the ${expected.length} pages failed against ${BASE}.\n\n` +
			'  That is an unreachable origin, not a prerender problem — check the host,\n' +
			'  DNS and TLS before reading anything into the list above.\n'
	);
	process.exit(1);
}

console.error(
	`\n✗ ${broken.length} of ${expected.length} pages are missing or serving the shell.\n\n` +
		'  These exist in this commit\'s fixtures but not as built pages, which means\n' +
		'  the web build ran before the api release held them. The fix is a commit\n' +
		'  touching frontend/ to force a rebuild now that the api has the rows —\n' +
		'  see the prerender-refresh notes atop src/routes/authors/[slug]/+page.ts.\n\n' +
		'  ONE OTHER EXPLANATION for a missing BOOK: `is_published` is create-only in\n' +
		'  seed_books, so an urgent unpublish on prod does not come back to the\n' +
		'  fixture. If a title here was pulled deliberately, set is_published false\n' +
		'  in its fixture rather than forcing a rebuild that cannot help.\n'
);
process.exit(1);
