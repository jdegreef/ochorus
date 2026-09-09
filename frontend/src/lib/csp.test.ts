/**
 * The CSP must keep up with the code.
 *
 * A Content-Security-Policy fails in the worst possible way: silently, in
 * production, only for the feature nobody re-tested. Add a `fetch` to a new host
 * and everything passes locally (no CSP on the dev server) and in CI (same),
 * then that one feature is dead on the live site.
 *
 * The policy now lives in `svelte.config.js` (`kit.csp`, hash mode) and ships as
 * a <meta> on every prerendered page — NOT as a render.yaml header any more, so
 * that `script-src` can drop `'unsafe-inline'` (a static header cannot carry the
 * hash of SvelteKit's per-build inline bootstrap). This test asserts the policy
 * against its source rather than trusting it:
 *
 *  - every absolute URL the app can dial is checked against `connect-src`;
 *  - the directives whose whole job is to hold the line are pinned;
 *  - `script-src` must NOT carry `'unsafe-inline'` (the point of the change); and
 *  - the app.html theme-boot script's hash in the config must match the actual
 *    script, so editing app.html without updating the hash fails the build
 *    instead of silently blocking the boot script in production.
 *
 * The non-CSP security headers still live in render.yaml and are checked there.
 */
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { describe, expect, it } from 'vitest';

import { cspDirectives as CSP_DIRECTIVES } from '../../csp.config.js';

const REPO_ROOT = path.resolve(__dirname, '../../..');
const RENDER_YAML = path.join(REPO_ROOT, 'render.yaml');
const APP_HTML = path.resolve(__dirname, '../app.html');
const SRC = path.resolve(__dirname, '..');

/**
 * CSP directives as configured in svelte.config.js. SvelteKit writes keyword
 * sources without the CSP quotes (`self`, not `'self'`), so assertions below
 * use that unquoted form. Hash/`unsafe-hashes` sources are written verbatim.
 */
function cspDirectives(): Record<string, string[]> {
	expect(CSP_DIRECTIVES, 'cspDirectives missing from csp.config.js').toBeTruthy();
	return CSP_DIRECTIVES as Record<string, string[]>;
}

/** The web service's non-CSP headers, read straight out of render.yaml. */
function webHeaders(): Record<string, string> {
	// Whole-line comments are dropped first: render.yaml explains itself at
	// length, and a comment sitting between a folded value and the next key is
	// otherwise indistinguishable from more value.
	const raw = fs
		.readFileSync(RENDER_YAML, 'utf8')
		.split('\n')
		.filter((line) => !/^\s*#/.test(line))
		.join('\n');

	// The `ochorus-web` service block, up to the next top-level list item.
	const start = raw.indexOf('- name: ochorus-web');
	expect(start, 'ochorus-web service not found in render.yaml').toBeGreaterThan(-1);
	const block = raw.slice(start);

	const headers: Record<string, string> = {};
	// `- path: /*` / `name: X` / `value: …` triples, where value may be a folded
	// (`>-`) scalar spanning lines. Indentation ends each entry.
	const re = /- path: \/\*\s*\n\s*name: (\S+)\s*\n\s*value: (>-\s*\n([\s\S]*?)(?=\n\s{6}- |\n\s{4}\w)|.+)/g;
	for (const m of block.matchAll(re)) {
		const folded = m[3];
		const value = folded
			? folded.replace(/\s+/g, ' ').trim()
			: m[2].trim().replace(/^["']|["']$/g, '');
		headers[m[1]] = value;
	}
	return headers;
}

/** The SHA-256 CSP source for app.html's inline theme-boot <script>. */
function bootScriptHash(): string {
	const html = fs.readFileSync(APP_HTML, 'utf8');
	const scripts = [...html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/g)];
	const boot = scripts.find(
		(m) => !/\bsrc=/.test(m[1]) && m[2].includes('localStorage') && m[2].includes('data-theme')
	);
	expect(boot, 'theme-boot <script> not found in app.html').toBeTruthy();
	const digest = crypto.createHash('sha256').update(boot![2]).digest('base64');
	return `sha256-${digest}`;
}

/** Every absolute http(s) origin the app's own code can dial. */
function originsUsedInSource(): Set<string> {
	const found = new Set<string>();
	const walk = (dir: string) => {
		for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
			const p = path.join(dir, entry.name);
			if (entry.isDirectory()) {
				if (entry.name === 'paraglide') continue; // generated
				walk(p);
				continue;
			}
			if (!/\.(ts|svelte)$/.test(entry.name)) continue;
			if (/\.test\.ts$/.test(entry.name)) continue;
			const code = fs.readFileSync(p, 'utf8');
			// Only URLs inside a fetch-ish call — a link in markup is navigation,
			// which CSP's connect-src does not govern.
			for (const m of code.matchAll(
				/(?:fetch|apiFetch|apiFetchRaw|EventSource|WebSocket|sendBeacon)\s*\(\s*[`'"]?(https:\/\/[a-zA-Z0-9.-]+)/g
			)) {
				found.add(m[1]);
			}
			// Template-literal fetches: `https://host/...` on its own line.
			for (const m of code.matchAll(/[`'"](https:\/\/[a-zA-Z0-9.-]+)\/api\//g)) {
				found.add(m[1]);
			}
		}
	};
	walk(SRC);
	return found;
}

function covers(sources: string[], origin: string): boolean {
	const host = new URL(origin).host;
	return sources.some((s) => {
		if (s === origin || s === `${origin}/`) return true;
		if (!s.startsWith('https://')) return false;
		const pattern = s.slice('https://'.length).replace(/\/$/, '');
		if (pattern === host) return true;
		if (pattern.startsWith('*.')) return host.endsWith(pattern.slice(1));
		return false;
	});
}

describe('render.yaml non-CSP security headers', () => {
	const headers = webHeaders();

	it('ships the headers that cost nothing and are easy to lose', () => {
		expect(headers['X-Content-Type-Options']).toBe('nosniff');
		expect(headers['X-Frame-Options']).toBe('DENY');
		expect(headers['Referrer-Policy']).toBe('strict-origin-when-cross-origin');
		expect(headers['Permissions-Policy']).toBeTruthy();
	});

	it('no longer carries the CSP as a header (it moved to kit.csp)', () => {
		// A leftover header CSP would enforce a second, stale policy alongside the
		// meta one — most confusingly, re-introducing 'unsafe-inline'.
		expect(headers['Content-Security-Policy']).toBeUndefined();
	});
});

describe('kit.csp Content-Security-Policy (svelte.config.js)', () => {
	it('locks the directives that hold the line', () => {
		const d = cspDirectives();
		expect(d['frame-ancestors']).toEqual(['none']);
		expect(d['object-src']).toEqual(['none']);
		expect(d['base-uri']).toEqual(['self']);
		expect(d['form-action']).toEqual(['self']);
		expect(d['default-src']).toEqual(['self']);
	});

	it('does NOT allow unsafe-inline scripts — the whole point of hash mode', () => {
		const script = cspDirectives()['script-src'];
		expect(script).toBeTruthy();
		expect(script).not.toContain('unsafe-inline');
		// A hash source proves inline scripts are admitted by hash, not blanket.
		expect(script.some((s) => s.startsWith('sha256-'))).toBe(true);
	});

	it('pins the app.html theme-boot hash to the actual script', () => {
		// SvelteKit hashes the scripts IT emits, but not the template boot script;
		// its hash is pinned by hand in the config. If app.html changes and the
		// hash is not updated, the boot script would be blocked in production —
		// fail here instead.
		const script = cspDirectives()['script-src'];
		expect(
			script,
			`script-src is missing the app.html theme-boot hash. app.html changed — ` +
				`update the hash in svelte.config.js to ${bootScriptHash()}`
		).toContain(bootScriptHash());
	});

	it('never allows a wildcard or plain-http connect-src', () => {
		// connect-src is the control that stops an injected script posting the
		// localStorage access token off-origin, so "*" would give the whole
		// policy away.
		const connect = cspDirectives()['connect-src'];
		expect(connect).toBeTruthy();
		expect(connect).not.toContain('*');
		expect(connect.some((s) => s.startsWith('http://'))).toBe(false);
		expect(connect).toContain('self');
	});

	it('pins the Supabase host to the exact project, not a wildcard', () => {
		// Anyone can create a free `<ref>.supabase.co`, so `*.supabase.co` would let
		// an injected script POST the localStorage token to an attacker-controlled
		// Supabase project — the exact exfiltration connect-src exists to stop.
		const connect = cspDirectives()['connect-src'];
		expect(connect.some((s) => s.includes('*.supabase.co'))).toBe(false);
		expect(connect.some((s) => /^https:\/\/[a-z0-9]+\.supabase\.co$/.test(s))).toBe(true);
	});

	it('covers every host the app actually fetches', () => {
		const connect = cspDirectives()['connect-src'];
		const used = [...originsUsedInSource()];
		// Guard against the scan silently matching nothing and passing vacuously.
		expect(used.length).toBeGreaterThan(0);
		// Normalise `self` → https:// origins are compared by host in covers().
		const sources = connect.map((s) => (s === 'self' ? "'self'" : s));
		const uncovered = used.filter((o) => !covers(sources, o));
		expect(
			uncovered,
			`These hosts are fetched in src/ but are not in the CSP connect-src ` +
				`(svelte.config.js). They will be blocked in production:\n  ${uncovered.join('\n  ')}`
		).toEqual([]);
	});
});
