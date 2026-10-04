#!/usr/bin/env node
/**
 * Upload the browser bundle's source maps to Sentry, then delete them.
 *
 * Without maps, a browser error in Sentry is one minified line: the release
 * says WHICH build broke but not where. With them, the stack names the file,
 * line and function in src/.
 *
 * Runs in postbuild, over the FINAL files in build/_app/immutable, after every
 * other step that rewrites a chunk. (Sentry's Vite plugin would run inside
 * SvelteKit's two Vite builds, before `absoluteAssetUrls` and adapter-static
 * have finished with the files.) It uses the "debug ID" method: each chunk and
 * its map get a matching ID, so the upload needs no URL prefixes to line up.
 *
 * Opt-in, like the DSN: it does nothing but the deletion below unless the build
 * has SENTRY_AUTH_TOKEN, SENTRY_ORG and SENTRY_PROJECT (vite.config.ts only
 * emits maps when the token is there). A failed upload WARNS and the deploy goes
 * on: monitoring must never be the reason the site didn't ship.
 *
 * The maps are always deleted from build/ afterwards, uploaded or not, because
 * serving them would publish the source.
 */
import { readdirSync, rmSync } from 'node:fs';
import { join, resolve } from 'node:path';

const BUILD = resolve(process.argv[2] || 'build');
const ASSETS = join(BUILD, '_app', 'immutable');
const { SENTRY_AUTH_TOKEN, SENTRY_ORG, SENTRY_PROJECT, RENDER_GIT_COMMIT } = process.env;

function mapsUnder(dir) {
	return readdirSync(dir, { recursive: true, withFileTypes: true })
		.filter((e) => e.isFile() && e.name.endsWith('.map'))
		.map((e) => join(e.parentPath, e.name));
}

/** Errors the Sentry manager reported. It hands them to `errorHandler` and
 * carries on rather than throwing, so a 401 would otherwise read as success. */
const failures = [];

async function upload() {
	const { createSentryBuildPluginManager } = await import('@sentry/bundler-plugins/core');
	const manager = createSentryBuildPluginManager(
		{
			org: SENTRY_ORG,
			project: SENTRY_PROJECT,
			authToken: SENTRY_AUTH_TOKEN,
			telemetry: false,
			// The browser SDK is told its release in hooks.client.ts (__RELEASE__);
			// this only names the release the maps are filed under.
			release: { name: RENDER_GIT_COMMIT || undefined, inject: false },
			errorHandler: (err) => failures.push(err.message)
		},
		{ buildTool: 'sveltekit-static', loggerPrefix: '[sentry-sourcemaps]' }
	);
	// A release needs a name; without RENDER_GIT_COMMIT (a manual build) the
	// debug-ID upload below still works, and creating one would only fail.
	if (RENDER_GIT_COMMIT) await manager.createRelease();
	await manager.injectDebugIds([ASSETS]);
	await manager.uploadSourcemaps([ASSETS]);
}

const configured = SENTRY_AUTH_TOKEN && SENTRY_ORG && SENTRY_PROJECT;
if (configured) {
	const found = mapsUnder(ASSETS).length;
	if (!found) {
		console.warn('[sentry-sourcemaps] no .map files under build/_app/immutable — nothing to upload');
	} else {
		try {
			await upload();
		} catch (err) {
			failures.push(String(err));
		}
		if (failures.length) {
			console.warn('[sentry-sourcemaps] upload FAILED, deploying without maps:');
			for (const f of failures) console.warn(`  ${f}`);
		} else {
			console.log(`[sentry-sourcemaps] uploaded ${found} source maps`);
		}
	}
} else {
	console.log('[sentry-sourcemaps] SENTRY_AUTH_TOKEN/ORG/PROJECT not set — skipping upload');
}

const leftover = mapsUnder(BUILD);
for (const file of leftover) rmSync(file);
if (leftover.length) console.log(`[sentry-sourcemaps] deleted ${leftover.length} .map files from build/`);
