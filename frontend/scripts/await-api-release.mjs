/**
 * Wait for the API to hold THIS build's content before prerendering against it.
 *
 * The reader is a static site prerendered from the API, and a content commit
 * deploys both services at once (render.yaml's buildFilter names the same
 * content roots this checks). So the web build can start while the API is
 * still serving the PREVIOUS release — and bake the old content into exactly
 * the pages the rebuild existed to freshen. It fails silently: the build goes
 * green, the content looks unchanged, and the next unrelated deploy quietly
 * fixes it. (svelte.config.js already carries a comment excusing routes that
 * "lag a simultaneous deploy" — this is that lag.)
 *
 * So: poll /api/health/ until its `content_version` matches the content in
 * this checkout, then let the build proceed. Waiting rather than failing is the
 * point — the API is mid-deploy, not broken, and a build that waits two minutes
 * ships correct content where a build that fails ships nothing.
 *
 * WHY CONTENT AND NOT THE COMMIT. Only ochorus-api has `rootDir: backend`, and
 * Render skips a service's build when nothing under its rootDir changed. A
 * frontend-only commit therefore deploys the web service ALONE, and the API
 * legitimately keeps reporting an older SHA forever — a gate comparing SHAs
 * would hang every frontend deploy for its full timeout and then fail it. The
 * narrower question this asks always has an answer: a frontend-only commit
 * leaves the content untouched, so the digests match on the first poll and the
 * build proceeds immediately.
 *
 * SKIPS (exit 0) rather than blocking whenever it cannot make a real comparison:
 * outside Render, with no API configured, with no content to read, or against
 * an API old enough not to publish `content_version` yet. A guard that hangs a
 * local or CI build to protect a race those builds don't have would be a worse
 * bug than the one it prevents.
 */

import { createHash } from 'node:crypto';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, relative, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const API = (process.env.PUBLIC_API_BASE_URL || '').replace(/\/+$/, '');
const ON_RENDER = Boolean((process.env.RENDER_GIT_COMMIT || '').trim());
const ENDPOINT = `${API}/api/health/`;

/**
 * The roots come from backend/library/content_sources.json — the same file
 * content_fixtures.py reads and render.yaml's buildFilter mirrors — so the
 * three cannot drift. The ALGORITHM is duplicated here and must stay in step
 * with content_digest(): every file under every root, keyed by
 * "<root>/<path relative to root>", roots sorted, paths sorted within a root.
 */
const BACKEND = fileURLToPath(new URL('../../backend', import.meta.url));
const SOURCES_FILE = join(BACKEND, 'library', 'content_sources.json');

/** How long to wait for the API's deploy to land before giving up. */
const TIMEOUT_MS = Number(process.env.API_RELEASE_TIMEOUT_MS || 5 * 60 * 1000);
const POLL_MS = 5000;

const skip = (why) => {
	console.log(`• api content check skipped — ${why}`);
	process.exit(0);
};

/** Every file under dir, as paths relative to it, POSIX-separated and sorted. */
function filesUnder(dir, base = dir, out = []) {
	for (const name of readdirSync(dir)) {
		const path = join(dir, name);
		if (statSync(path).isDirectory()) filesUnder(path, base, out);
		else out.push(relative(base, path).split(sep).join('/'));
	}
	return out.sort();
}

/** The digest of this checkout's reader content, or null if it isn't readable. */
function localDigest() {
	let roots;
	try {
		roots = JSON.parse(readFileSync(SOURCES_FILE, 'utf8')).roots;
	} catch {
		return null; // not a full checkout (shallow build context, npm pack, …)
	}
	const h = createHash('sha256');
	let seen = 0;
	for (const root of [...roots].sort()) {
		const dir = join(BACKEND, root);
		let files;
		try {
			files = filesUnder(dir);
		} catch {
			continue; // a root that doesn't exist yet is skipped, as Python does
		}
		for (const rel of files) {
			seen += 1;
			h.update(`${root}/${rel}`);
			h.update('\0');
			h.update(createHash('sha256').update(readFileSync(join(dir, rel))).digest('hex'));
			h.update('\0');
		}
	}
	return seen ? h.digest('hex').slice(0, 16) : null;
}

if (!ON_RENDER) skip('RENDER_GIT_COMMIT unset (not a Render build)');
if (!API) skip('PUBLIC_API_BASE_URL unset');

const WANT = localDigest();
if (!WANT) skip('no reader content in this build context');

/** The content version the API reports, or null if it can't be read this attempt. */
async function apiContent() {
	try {
		const res = await fetch(ENDPOINT, { headers: { accept: 'application/json' } });
		if (!res.ok) return null;
		const body = await res.json();
		// `undefined` = an API predating this field, which the caller skips on.
		return typeof body.content_version === 'string' ? body.content_version.trim() : undefined;
	} catch {
		return null;
	}
}

const started = Date.now();
let attempts = 0;

while (Date.now() - started < TIMEOUT_MS) {
	const serving = await apiContent();
	attempts += 1;

	if (serving === undefined) skip('this API does not publish a content version yet');

	if (serving === WANT) {
		const waited = Math.round((Date.now() - started) / 1000);
		console.log(
			`✓ api holds this build's content (${WANT})` +
				(waited ? ` — waited ${waited}s for its deploy to land` : '')
		);
		process.exit(0);
	}

	if (attempts === 1) {
		console.log(
			`• api holds ${serving || '(unreachable)'}, this build has ${WANT} — ` +
				'waiting for its deploy to catch up…'
		);
	}
	await new Promise((r) => setTimeout(r, POLL_MS));
}

console.error(
	`\n✗ api content check: timed out after ${Math.round(TIMEOUT_MS / 1000)}s.\n` +
		`  This build's content digests to ${WANT}; the API never reported it.\n\n` +
		'  Prerendering now would bake the PREVIOUS release’s content into pages\n' +
		'  meant to show this one, and it would do so silently — so the build stops\n' +
		'  instead. Check the ochorus-api deploy: if it failed, fix that and redeploy\n' +
		`  the web service. Endpoint: ${ENDPOINT}\n`
);
process.exit(1);
