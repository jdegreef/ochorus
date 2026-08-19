/**
 * Wait for the API to be serving THIS commit before prerendering against it.
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
 * So: poll /api/health/ until its `commit` matches the commit being built, then
 * let the build proceed. Waiting rather than failing is the point — the API is
 * mid-deploy, not broken, and a build that waits two minutes ships correct
 * content where a build that fails ships nothing.
 *
 * SKIPS (exit 0) rather than blocking whenever it cannot make a real comparison:
 * outside Render (no RENDER_GIT_COMMIT), with no API configured, or against an
 * API old enough not to publish `commit` yet. A guard that hangs a local or CI
 * build to protect a race those builds don't have would be a worse bug than the
 * one it prevents.
 */

const API = (process.env.PUBLIC_API_BASE_URL || '').replace(/\/+$/, '');
const BUILDING = (process.env.RENDER_GIT_COMMIT || '').trim();
const ENDPOINT = `${API}/api/health/`;

/** How long to wait for the API's deploy to land before giving up. */
const TIMEOUT_MS = Number(process.env.API_RELEASE_TIMEOUT_MS || 5 * 60 * 1000);
const POLL_MS = 5000;

const skip = (why) => {
	console.log(`• api release check skipped — ${why}`);
	process.exit(0);
};

if (!BUILDING) skip('RENDER_GIT_COMMIT unset (not a Render build)');
if (!API) skip('PUBLIC_API_BASE_URL unset');

/** The commit the API reports, or null if it can't be read this attempt. */
async function apiCommit() {
	try {
		const res = await fetch(ENDPOINT, { headers: { accept: 'application/json' } });
		if (!res.ok) return null;
		const body = await res.json();
		// `undefined` = an API predating this field; '' = deployed outside Render.
		// Both mean "no comparison possible", which the caller treats as a skip.
		return typeof body.commit === 'string' ? body.commit.trim() : undefined;
	} catch {
		return null;
	}
}

const started = Date.now();
let attempts = 0;

while (Date.now() - started < TIMEOUT_MS) {
	const commit = await apiCommit();
	attempts += 1;

	if (commit === undefined) skip('this API does not publish a commit yet');
	if (commit === '') skip('the API reports no commit (deployed outside Render)');

	if (commit === BUILDING) {
		const waited = Math.round((Date.now() - started) / 1000);
		console.log(
			`✓ api is serving ${BUILDING.slice(0, 8)}` +
				(waited ? ` (waited ${waited}s for its deploy to land)` : '')
		);
		process.exit(0);
	}

	if (attempts === 1) {
		console.log(
			`• api is serving ${commit ? commit.slice(0, 8) : '(unreachable)'}, ` +
				`this build is ${BUILDING.slice(0, 8)} — waiting for it to catch up…`
		);
	}
	await new Promise((r) => setTimeout(r, POLL_MS));
}

console.error(
	`\n✗ api release check: timed out after ${Math.round(TIMEOUT_MS / 1000)}s.\n` +
		`  This build is ${BUILDING.slice(0, 8)}; the API never started serving it.\n\n` +
		'  Prerendering now would bake the PREVIOUS release’s content into pages\n' +
		'  meant to show this one, and it would do so silently — so the build stops\n' +
		'  instead. Check the ochorus-api deploy: if it failed, fix that and redeploy\n' +
		`  the web service. Endpoint: ${ENDPOINT}\n`
);
process.exit(1);
