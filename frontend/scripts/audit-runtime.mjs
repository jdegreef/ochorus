#!/usr/bin/env node
/**
 * The dependency audit's npm gate (.github/workflows/dependency-audit.yml):
 * `npm audit --omit=dev`, failing on any high or critical advisory in the
 * runtime tree, EXCEPT the ones listed in ALLOWED below.
 *
 * An advisory belongs here only when it cannot be fixed by a bump today AND
 * this site cannot be reached by it. Each entry says why, and what retires it.
 * The gate also fails on a STALE entry (an allowed advisory npm no longer
 * reports), so a fixed advisory leaves the list in the same PR that fixes it
 * instead of lingering as a silent exemption.
 *
 *   node scripts/audit-runtime.mjs          # what CI runs
 */
import { execFileSync } from 'node:child_process';
import { pathToFileURL } from 'node:url';

/** Severities that fail the gate (npm audit's `--audit-level=high`). */
const BLOCKING = new Set(['high', 'critical']);

/**
 * GHSA id → why it does not apply here, and what retires it.
 * @type {Record<string, { package: string, reason: string, retire: string }>}
 */
export const ALLOWED = {
	'GHSA-3r8g-jcqq-3p5j': {
		package: '@sveltejs/kit',
		reason:
			'DoS while parsing form data from a remote functions `form`. Ochorus uses no ' +
			'remote functions (nothing imports $app/server; no *.remote.* modules), and ' +
			'the site is a static build (adapter-static): no SvelteKit server runs in ' +
			'production to receive a form.',
		retire:
			'Fixed only in @sveltejs/kit 3.x — the planned Kit 3 migration (#5329, #5330; ' +
			'see .github/dependabot.yml). Remove this entry in that PR.'
	},
	'GHSA-fc5q-39xc-vjpf': {
		package: 'picomatch',
		reason:
			'ReDoS through an attacker-supplied single-branch repeated extglob (e.g. +(*)). ' +
			'picomatch reaches the runtime tree only through vite/tinyglobby/fdir, which run ' +
			'at build time on glob patterns written in this repo; no visitor input is ever ' +
			'compiled as a glob.',
		retire:
			'No patched release exists (4.0.7 is the latest and is affected). Remove this ' +
			'entry once a fixed picomatch lands in package-lock.json.'
	}
};

/** @param {unknown} url */
const ghsaOf = (url) =>
	/GHSA-[0-9a-z]{4}-[0-9a-z]{4}-[0-9a-z]{4}/i.exec(String(url ?? ''))?.[0] ?? null;

/**
 * Judge an `npm audit --json` report against the allowlist.
 * Advisories are the objects in each vulnerability's `via` (a string `via` only
 * points at another package's entry, so each advisory is seen at its source).
 * @param {{ vulnerabilities?: Record<string, { via: Array<string | Record<string, unknown>> }> }} report
 * @param {Record<string, unknown>} [allowed]
 */
export function evaluate(report, allowed = ALLOWED) {
	const seen = new Map();
	for (const vuln of Object.values(report.vulnerabilities ?? {})) {
		for (const via of vuln.via ?? []) {
			if (typeof via !== 'object' || via === null) continue;
			const id = ghsaOf(via.url) ?? String(via.source);
			seen.set(id, { id, package: via.name, severity: via.severity, title: via.title, url: via.url });
		}
	}
	const advisories = [...seen.values()];
	return {
		blocking: advisories.filter((a) => BLOCKING.has(a.severity) && !(a.id in allowed)),
		allowed: advisories.filter((a) => a.id in allowed),
		stale: Object.keys(allowed).filter((id) => !seen.has(id))
	};
}

function main() {
	let raw;
	try {
		raw = execFileSync('npm', ['audit', '--omit=dev', '--json'], { encoding: 'utf8' });
	} catch (err) {
		// npm audit exits non-zero whenever it finds anything; the report is still on stdout.
		raw = /** @type {{ stdout?: string }} */ (err).stdout;
		if (!raw) throw err;
	}
	const { blocking, allowed, stale } = evaluate(JSON.parse(raw));

	for (const a of allowed) {
		console.log(`allowed  ${a.id}  ${a.package} (${a.severity}): ${ALLOWED[a.id].reason}`);
	}
	for (const a of blocking) {
		console.log(`BLOCKING ${a.id}  ${a.package} (${a.severity}): ${a.title}\n         ${a.url}`);
	}
	for (const id of stale) {
		console.log(
			`STALE    ${id}  is allowed in scripts/audit-runtime.mjs but npm no longer reports it — ` +
				'remove the entry.'
		);
	}
	if (blocking.length || stale.length) process.exit(1);
	console.log(`npm audit: no unallowed high/critical advisories (${allowed.length} allowed).`);
}

if (import.meta.url === pathToFileURL(process.argv[1] ?? '').href) main();
