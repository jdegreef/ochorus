/**
 * The CSP in render.yaml must keep up with the code.
 *
 * A Content-Security-Policy fails in the worst possible way: silently, in
 * production, only for the feature nobody re-tested. Add a `fetch` to a new host
 * and everything passes locally (no CSP on the dev server) and in CI (same),
 * then that one feature is dead on the live site.
 *
 * So the policy is asserted against the source rather than trusted: every
 * absolute URL the app can dial is checked against `connect-src`. If someone
 * adds an integration and forgets the header, this fails in CI instead.
 *
 * It also pins the directives whose whole job is to hold the line — dropping
 * `frame-ancestors` or `object-src` would be invisible until someone exploited
 * it — and asserts the one thing `script-src 'unsafe-inline'` implies: that
 * `connect-src`, not `script-src`, is what protects the localStorage token.
 */
import fs from 'node:fs';
import path from 'node:path';
import { describe, expect, it } from 'vitest';

const REPO_ROOT = path.resolve(__dirname, '../../..');
const RENDER_YAML = path.join(REPO_ROOT, 'render.yaml');
const SRC = path.resolve(__dirname, '..');

/** The web service's headers, read straight out of render.yaml. */
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

function directives(csp: string): Record<string, string[]> {
	const out: Record<string, string[]> = {};
	for (const part of csp.split(';')) {
		const [name, ...values] = part.trim().split(/\s+/);
		if (name) out[name] = values;
	}
	return out;
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

describe('render.yaml security headers', () => {
	const headers = webHeaders();

	it('sets a Content-Security-Policy on every path', () => {
		expect(headers['Content-Security-Policy']).toBeTruthy();
	});

	it('ships the headers that cost nothing and are easy to lose', () => {
		expect(headers['X-Content-Type-Options']).toBe('nosniff');
		expect(headers['X-Frame-Options']).toBe('DENY');
		expect(headers['Referrer-Policy']).toBe('strict-origin-when-cross-origin');
		expect(headers['Permissions-Policy']).toBeTruthy();
	});

	it('locks the directives that hold the line', () => {
		const d = directives(headers['Content-Security-Policy']);
		expect(d['frame-ancestors']).toEqual(["'none'"]);
		expect(d['object-src']).toEqual(["'none'"]);
		expect(d['base-uri']).toEqual(["'self'"]);
		expect(d['form-action']).toEqual(["'self'"]);
		expect(d['default-src']).toEqual(["'self'"]);
	});

	it('never allows a wildcard or plain-http connect-src', () => {
		// connect-src is the control that stops an injected script posting the
		// localStorage access token off-origin, so "*" would give the whole
		// policy away.
		const connect = directives(headers['Content-Security-Policy'])['connect-src'];
		expect(connect).toBeTruthy();
		expect(connect).not.toContain('*');
		expect(connect.some((s) => s.startsWith('http://'))).toBe(false);
		expect(connect).toContain("'self'");
	});

	it('pins the Supabase host to the exact project, not a wildcard', () => {
		// Anyone can create a free `<ref>.supabase.co`, so `*.supabase.co` would let
		// an injected script POST the localStorage token to an attacker-controlled
		// Supabase project — the exact exfiltration connect-src exists to stop.
		// (The bare-`*` check above misses this: `https://*.supabase.co` !== '*'.)
		const connect = directives(headers['Content-Security-Policy'])['connect-src'];
		expect(connect.some((s) => s.includes('*.supabase.co'))).toBe(false);
		expect(connect.some((s) => /^https:\/\/[a-z0-9]+\.supabase\.co$/.test(s))).toBe(true);
	});

	it('covers every host the app actually fetches', () => {
		const connect = directives(headers['Content-Security-Policy'])['connect-src'];
		const used = [...originsUsedInSource()];
		// Guard against the scan silently matching nothing and passing vacuously.
		expect(used.length).toBeGreaterThan(0);
		const uncovered = used.filter((o) => !covers(connect, o));
		expect(
			uncovered,
			`These hosts are fetched in src/ but are not in the CSP connect-src ` +
				`(render.yaml). They will be blocked in production:\n  ${uncovered.join('\n  ')}`
		).toEqual([]);
	});
});
