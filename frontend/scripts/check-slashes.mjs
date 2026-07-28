#!/usr/bin/env node
/**
 * Trailing-slash audit.
 *
 * The six detail routes prerender to `<slug>/index.html`. Render serves that for
 * the slash URL; the non-slash URL used to fall through to the `/* -> /200.html`
 * SPA catch-all and return an empty shell — no <title>, no content — which is
 * what crawlers saw, because every internal link emitted the non-slash form.
 *
 * This fetches every URL in the sitemap in BOTH forms and reports status, byte
 * size and whether a <title> is present, so the two can be compared directly.
 *
 *   node scripts/check-slashes.mjs                        # production
 *   node scripts/check-slashes.mjs --base http://localhost:4173
 *   node scripts/check-slashes.mjs --limit 40             # sample, for a quick pass
 *   node scripts/check-slashes.mjs --sitemap ../build/sitemap.xml
 *
 * FAILS (exit 1) only on a broken CANONICAL — a slash URL that is missing or is
 * itself a shell. That is the property the site actually guarantees.
 *
 * The non-slash column is REPORTED, not asserted. There is deliberately no
 * no-slash -> slash 301: Render's route matcher is trailing-slash-insensitive,
 * so such a rule also matches the slashed form and infinite-loops on any path
 * with no prerendered file (see render.yaml). Those URLs therefore keep serving
 * the SPA shell until search engines recanonicalize from the corrected links and
 * sitemap. Asserting on them would mean this script could never pass — which is
 * how a check ends up ignored.
 *
 * A POST-DEPLOY probe, not a CI gate — it needs a deployed host. The CI-safe
 * counterpart is the build-output assertion in src/lib/href.test.ts.
 */

import { readFile } from 'node:fs/promises';

const args = process.argv.slice(2);
const opt = (name, fallback = null) => {
	const i = args.indexOf(`--${name}`);
	return i !== -1 && args[i + 1] ? args[i + 1] : fallback;
};

const BASE = (opt('base', 'https://ochorus.com')).replace(/\/$/, '');
const LIMIT = Number(opt('limit', '0')) || 0;
const SITEMAP = opt('sitemap');
const CONCURRENCY = Number(opt('concurrency', '8'));

/** A response with no <title> and a tiny body is the SPA fallback shell. */
const SHELL_MAX_BYTES = 8000;

async function sitemapUrls() {
	const xml = SITEMAP
		? await readFile(SITEMAP, 'utf8')
		: await fetch(`${BASE}/sitemap.xml`).then((r) => {
				if (!r.ok) throw new Error(`sitemap fetch failed: ${r.status}`);
				return r.text();
			});
	const locs = [...xml.matchAll(/<loc>([^<]+)<\/loc>/g)].map((m) => m[1].trim());
	if (!locs.length) throw new Error('no <loc> entries found in the sitemap');
	return locs;
}

async function probe(url) {
	try {
		// `manual` so a 301 is reported as a 301 rather than silently followed —
		// the redirect is the fix for the non-slash form, so it must be visible.
		const res = await fetch(url, { redirect: 'manual' });
		const body = res.status >= 300 && res.status < 400 ? '' : await res.text();
		return {
			url,
			status: res.status,
			location: res.headers.get('location') ?? '',
			bytes: Buffer.byteLength(body),
			hasTitle: /<title[^>]*>[^<]*\S[^<]*<\/title>/i.test(body)
		};
	} catch (err) {
		return { url, status: 0, location: '', bytes: 0, hasTitle: false, error: String(err) };
	}
}

/** Simple concurrency pool — the sitemap can hold a couple of thousand URLs. */
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
const pad = (s, n) => String(s).padEnd(n);

const all = await sitemapUrls();
// Only the nested detail routes ever had the split brain; index pages resolve
// either way via explicit Render rewrites.
const detail = all.filter((u) => /\/(books|authors|topics|sermons|plans)\/[^/]+\/?$/.test(u)
	|| /\/books\/[^/]+\/\d+\/?$/.test(u));
const chosen = LIMIT ? detail.slice(0, LIMIT) : detail;

console.log(`sitemap: ${all.length} URLs (${detail.length} detail) — checking ${chosen.length} against ${BASE}\n`);

const pairs = chosen.map((u) => {
	const path = u.replace(/^https?:\/\/[^/]+/, '');
	const slash = path.endsWith('/') ? path : `${path}/`;
	return { slash: BASE + slash, plain: BASE + slash.replace(/\/$/, '') };
});

const slashRes = await mapPool(pairs.map((p) => p.slash), probe, CONCURRENCY);
const plainRes = await mapPool(pairs.map((p) => p.plain), probe, CONCURRENCY);

const brokenCanonical = slashRes.filter((r) => r.status !== 200 || isShell(r));
const plainShells = plainRes.filter(isShell);
const plainRedirects = plainRes.filter((r) => r.status === 301 || r.status === 308);
const plainOk = plainRes.filter((r) => r.status === 200 && r.hasTitle);

console.log('CANONICAL (with trailing slash)');
console.log(`  200 with <title> : ${slashRes.filter((r) => r.status === 200 && r.hasTitle).length}/${slashRes.length}`);
console.log(`  median bytes     : ${median(slashRes.map((r) => r.bytes))}`);
if (brokenCanonical.length) {
	console.log(`  !! BROKEN        : ${brokenCanonical.length}`);
	brokenCanonical.slice(0, 8).forEach((r) => console.log(`     ${pad(r.status, 4)} ${pad(r.bytes + 'b', 9)} ${r.url}`));
}

console.log('\nNON-SLASH (informational — no 301 by design, see the header)');
console.log(`  301/308 redirect : ${plainRedirects.length}`);
console.log(`  200 with <title> : ${plainOk.length}`);
console.log(`  200 shell        : ${plainShells.length}   (expected; recanonicalizes via links + sitemap)`);
plainShells.slice(0, 8).forEach((r) => console.log(`     ${pad(r.status, 4)} ${pad(r.bytes + 'b', 9)} ${r.url}`));

console.log('\nSAMPLE (both forms side by side)');
console.log(`  ${pad('path', 46)} ${pad('slash', 22)} non-slash`);
for (let i = 0; i < Math.min(6, pairs.length); i++) {
	const s = slashRes[i], p = plainRes[i];
	const path = pairs[i].slash.replace(BASE, '');
	console.log(
		`  ${pad(path, 46)} ${pad(`${s.status} ${s.bytes}b ${s.hasTitle ? 'title' : 'NO-TITLE'}`, 22)} ` +
			`${p.status} ${p.bytes}b ${p.hasTitle ? 'title' : p.status >= 300 && p.status < 400 ? '-> ' + p.location : 'NO-TITLE'}`
	);
}

function median(ns) {
	if (!ns.length) return 0;
	const s = [...ns].sort((a, b) => a - b);
	return s[Math.floor(s.length / 2)];
}

const failed = brokenCanonical.length > 0;
console.log(
	`\n${failed ? 'FAIL' : 'PASS'}: ${brokenCanonical.length} broken canonical` +
		` (${plainShells.length} non-slash shells, informational)`
);
process.exit(failed ? 1 : 0);
