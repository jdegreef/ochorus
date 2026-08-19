/**
 * Wait for the API to hold THIS build's content before prerendering against it.
 *
 * The reader is a static site prerendered from the API, and a content commit
 * deploys both services at once (render.yaml's buildFilter includes
 * backend/library/fixtures/**). So the web build can start while the API is
 * still serving the PREVIOUS release — and bake the old content into exactly
 * the pages the rebuild existed to freshen. It fails silently: the build goes
 * green, the content looks unchanged, and the next unrelated deploy quietly
 * fixes it. (svelte.config.js already carries a comment excusing routes that
 * "lag a simultaneous deploy" — this is that lag.)
 *
 * So: poll /api/health/ until its `content_version` matches the fixtures in
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
 * leaves the fixtures untouched, so the digests match on the first poll and the
 * build proceeds immediately.
 *
 * SKIPS (exit 0) rather than blocking whenever it cannot make a real comparison:
 * outside Render, with no API configured, with no fixtures to read, or against
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
 * Must stay in step with library/content_fixtures.py: content_digest() — every
 * *.json here, by sorted relative path. Scoped to content/ to match the
 * buildFilter that triggers this build; see that docstring for what falls
 * outside both.
 */
const CONTENT_DIR = fileURLToPath(new URL('../../backend/library/fixtures/content', import.meta.url));

/** How long to wait for the API's deploy to land before giving up. */
const TIMEOUT_MS = Number(process.env.API_RELEASE_TIMEOUT_MS || 5 * 60 * 1000);
const POLL_MS = 5000;

const skip = (why) => {
	console.log(`• api content check skipped — ${why}`);
	process.exit(0);
};

/** Every *.json under dir, as paths relative to it, POSIX-separated and sorted. */
function fixtureFiles(dir, base = dir, out = []) {
	for (const name of readdirSync(dir)) {
		const path = join(dir, name);
		if (statSync(path).isDirectory()) fixtureFiles(path, base, out);
		else if (name.endsWith('.json')) out.push(relative(base, path).split(sep).join('/'));
	}
	return out.sort();
}

/** The digest of this checkout's fixtures, or null if they aren't readable. */
function localDigest() {
	let files;
	try {
		files = fixtureFiles(CONTENT_DIR);
	} catch {
		return null; // not a full checkout (shallow build context, npm pack, …)
	}
	if (!files.length) return null;
	const h = createHash('sha256');
	for (const rel of files) {
		h.update(rel);
		h.update('\0');
		h.update(createHash('sha256').update(readFileSync(join(CONTENT_DIR, rel))).digest('hex'));
		h.update('\0');
	}
	return h.digest('hex').slice(0, 16);
}

if (!ON_RENDER) skip('RENDER_GIT_COMMIT unset (not a Render build)');
if (!API) skip('PUBLIC_API_BASE_URL unset');

const WANT = localDigest();
if (!WANT) skip('no content fixtures in this build context');

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
		`  This build's fixtures digest to ${WANT}; the API never reported it.\n\n` +
		'  Prerendering now would bake the PREVIOUS release’s content into pages\n' +
		'  meant to show this one, and it would do so silently — so the build stops\n' +
		'  instead. Check the ochorus-api deploy: if it failed, fix that and redeploy\n' +
		`  the web service. Endpoint: ${ENDPOINT}\n`
);
process.exit(1);
