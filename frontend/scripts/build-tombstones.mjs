#!/usr/bin/env node
/**
 * Overwrite every page an EARLIER deploy published and this build no longer
 * produces with the not-found shell — the last `postbuild` step.
 *
 * WHY. Render's static hosting keeps the files of previous deploys on purpose
 * (so a browser still running the old bundle can fetch its chunks), and a path
 * that is missing from the new build keeps serving the OLD file. adapter-static
 * wipes build/ every time, so nothing in this repo carries the page forward —
 * the host does. A withdrawn work therefore stayed readable, 200 and indexable,
 * at its old URL: The Marriage Tie (removed by migration 0200), Henry
 * Blackaby's biography in ten languages (0169), and the copyright-blocked
 * Grace for Grace es/fr/pt with every chapter (0164) were all still served
 * weeks later, while the API answered 404 and no page linked them.
 *
 * Deleting a file is the one thing a deploy cannot do on that host. Replacing
 * one is: the newest file at a path wins. So each build writes a TOMBSTONE —
 * a byte copy of build/404.html, the `noindex` SPA shell — at every path that
 * any earlier deploy published and this one does not. The withdrawn prose is
 * gone from the HTML; the router boots, asks the API, gets 404 and renders the
 * app's own not-found page. (The status stays 200 — a file the host serves is
 * a 200 — but the shell is `noindex`, so crawlers drop the URL.)
 *
 * WHICH PATHS. Every build publishes `published-pages.txt`: every HTML file in
 * build/, tombstones included, one per line. The next build fetches the LIVE
 * copy, so the list is cumulative: once a path has been served it is never
 * forgotten, and a work withdrawn in any later commit is tombstoned by the
 * first deploy that stops producing it. `withdrawn-pages.txt` (beside this
 * script) seeds the paths that went stale before the list existed.
 *
 * A work that comes BACK is prerendered again and its real page replaces the
 * tombstone — a tombstone is only ever written where the build has no file.
 *
 *   node scripts/build-tombstones.mjs [buildDir]
 *
 * Fetches the previous list only on Render (`RENDER` is set there) from
 * PUBLIC_SITE_URL, or from TOMBSTONE_PREVIOUS (a URL or a file) when given.
 * CI and local builds use the seed alone. On Render it FAILS THE BUILD if the
 * previous list can't be read — a 404 is accepted only on the very first
 * deploy, recognised by no seed page being tombstoned live yet — because a
 * deploy that silently skipped this step would publish a list missing the
 * paths it should have tombstoned, and they would never be found again. Set
 * TOMBSTONE_PREVIOUS=none to deploy anyway, knowing that.
 *
 * It also fails when more than TOMBSTONE_MAX (default 300) pages would be
 * tombstoned at once: that is a build short of pages, not a withdrawal.
 */
import { copyFileSync, existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { dirname, join, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

export const MANIFEST = 'published-pages.txt';
const SEED = join(dirname(fileURLToPath(import.meta.url)), 'withdrawn-pages.txt');
/** The two shells are the host's fallbacks, not pages: never listed, never tombstoned. */
const SHELLS = new Set(['200.html', '404.html']);
/** More withdrawals than this in one deploy fails the build (see main). */
const DEFAULT_MAX = 300;

/**
 * Every `.html` under `dir`, as forward-slashed paths relative to it.
 * @param {string} dir @param {string} [root] @param {string[]} [out]
 * @returns {string[]}
 */
export function htmlFiles(dir, root = dir, out = []) {
	for (const e of readdirSync(dir, { withFileTypes: true })) {
		const p = join(dir, e.name);
		if (e.isDirectory()) htmlFiles(p, root, out);
		else if (e.name.endsWith('.html')) out.push(relative(root, p).split(sep).join('/'));
	}
	return out;
}

/**
 * Parse a page list (the manifest or the seed): one build-relative `.html` path
 * per line; blank lines and `#` comments ignored. Anything else — an absolute
 * path, a `..`, a line that isn't an .html path — throws, so an HTML error page
 * served in the manifest's place can never be read as a list of paths.
 * @param {string} text @param {string} source
 * @returns {string[]}
 */
export function parsePageList(text, source) {
	const paths = [];
	for (const raw of text.split('\n')) {
		const line = raw.trim();
		if (!line || line.startsWith('#')) continue;
		if (!/^[^/\s][^\s]*\.html$/.test(line) || line.split('/').includes('..')) {
			throw new Error(`${source}: not a build-relative .html path: ${JSON.stringify(line.slice(0, 120))}`);
		}
		if (!SHELLS.has(line)) paths.push(line);
	}
	return paths;
}

/**
 * The paths to tombstone: known from before, absent from this build.
 * @param {string[]} known @param {string[]} built
 */
export function tombstonesFor(known, built) {
	const have = new Set(built);
	return [...new Set(known)].filter((p) => !have.has(p) && !SHELLS.has(p)).sort();
}

/** GET with a cache-busting query (the CDN holds responses ~5 minutes), retried. */
/** @param {string} url */
async function fetchFresh(url) {
	let lastError;
	for (let attempt = 1; attempt <= 3; attempt++) {
		try {
			const res = await fetch(`${url}?build=${Date.now()}`, { signal: AbortSignal.timeout(30_000) });
			if (res.status < 500) return { status: res.status, text: await res.text() };
			lastError = new Error(`${url} answered ${res.status}`);
		} catch (e) {
			lastError = e;
		}
		if (attempt < 3) await new Promise((r) => setTimeout(r, 2_000 * attempt));
	}
	throw lastError;
}

/**
 * Is this the first deploy to publish the list? Only if no seed page has been
 * tombstoned on the live site yet — every deploy with this step tombstones them
 * all. Once one has, a 404 for the list is a fault (a CDN hiccup, a changed
 * PUBLIC_SITE_URL), not a beginning, and going on would silently forget every
 * page this deploy withdraws.
 *
 * A tombstone is a byte copy of the deploy's shell, so it reads back identical
 * to the live /200.html. (Not "is it noindex": untranslated author pages are
 * noindex too.)
 * @param {string} origin @param {string[]} seed
 */
async function isFirstDeploy(origin, seed) {
	const shell = (await fetchFresh(`${origin}/200.html`)).text;
	for (const p of seed.slice(0, 3)) {
		const { text } = await fetchFresh(`${origin}/${p.replace(/index\.html$/, '')}`);
		if (text === shell) return false;
	}
	return true;
}

/**
 * The previous deploy's list, or [] where there is none to read.
 * @param {string[]} seed
 * @returns {Promise<string[]>}
 */
async function previousList(seed) {
	const configured = process.env.TOMBSTONE_PREVIOUS;
	if (configured === 'none') {
		console.warn('build-tombstones: TOMBSTONE_PREVIOUS=none — using the seed only');
		return [];
	}
	let source = configured;
	if (!source) {
		if (!process.env.RENDER) return [];
		const site = (process.env.PUBLIC_SITE_URL || '').replace(/\/+$/, '');
		if (!site) throw new Error('PUBLIC_SITE_URL is unset, so the live page list cannot be fetched.');
		source = `${site}/${MANIFEST}`;
	}
	if (!/^https?:\/\//.test(source)) return parsePageList(readFileSync(source, 'utf8'), source);

	const { status, text } = await fetchFresh(source);
	if (status === 404) {
		if (!(await isFirstDeploy(new URL(source).origin, seed))) {
			throw new Error(`${source} answered 404, but an earlier deploy already published it.`);
		}
		console.warn(`build-tombstones: no ${source} yet (first deploy with it) — using the seed only`);
		return [];
	}
	if (status !== 200) throw new Error(`${source} answered ${status}.`);
	return parsePageList(text, source);
}

/** @param {string} buildDir */
export async function main(buildDir) {
	const shell = join(buildDir, '404.html');
	if (!existsSync(shell)) throw new Error(`${shell} is missing — build-404 must run first.`);

	const seed = parsePageList(readFileSync(SEED, 'utf8'), SEED);
	const built = htmlFiles(buildDir).filter((p) => !SHELLS.has(p));
	const graves = tombstonesFor([...(await previousList(seed)), ...seed], built);

	// A build that is SHORT of pages — an API list answering partially during a
	// release — would otherwise blank every page it skipped, where the host's
	// leftover copy was at least right. Withdrawals come a work at a time; a
	// burst means something upstream is wrong. Withdrawing a whole language is
	// the legitimate exception: raise TOMBSTONE_MAX for that one deploy.
	const max = Number(process.env.TOMBSTONE_MAX) || DEFAULT_MAX;
	if (graves.length > max) {
		throw Object.assign(
			new Error(
				`${graves.length} previously published pages are missing from this build ` +
					`(limit ${max}), e.g. ${graves.slice(0, 5).map((p) => `/${p}`).join(', ')}.`
			),
			{ hint: 'If that many withdrawals are intended (a language taken offline), set TOMBSTONE_MAX above it for this deploy; otherwise find out why the build lost them.' }
		);
	}

	for (const p of graves) {
		const target = join(buildDir, p);
		mkdirSync(dirname(target), { recursive: true });
		copyFileSync(shell, target);
	}
	const published = [...new Set([...built, ...graves])].sort();
	writeFileSync(join(buildDir, MANIFEST), published.join('\n') + '\n');

	console.log(
		`build-tombstones: ${graves.length} withdrawn page(s) overwritten with the not-found shell; ` +
			`${published.length} paths in ${MANIFEST}`
	);
	for (const p of graves.slice(0, 20)) console.log(`  ✝ /${p.replace(/index\.html$/, '')}`);
	if (graves.length > 20) console.log(`  … and ${graves.length - 20} more`);
}

if (process.argv[1] && fileURLToPath(import.meta.url) === resolve(process.argv[1])) {
	main(resolve(process.cwd(), process.argv[2] ?? 'build')).catch((e) => {
		console.error(`\n✗ build-tombstones: ${e instanceof Error ? e.message : e}\n`);
		console.error(
			'  ' +
				(e?.hint ??
					'Without the previous page list, pages withdrawn by this deploy would keep\n' +
						'  serving their old HTML from the host forever. Fix the cause and redeploy, or\n' +
						'  set TOMBSTONE_PREVIOUS=none on ochorus-web to deploy without it (and then\n' +
						'  add any page this deploy withdraws to scripts/withdrawn-pages.txt).') +
				'\n'
		);
		process.exit(1);
	});
}
