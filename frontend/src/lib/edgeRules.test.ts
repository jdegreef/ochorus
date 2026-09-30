import { readFileSync, readdirSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import { isSlashedPath } from './canonicalRedirect';

/**
 * The Cloudflare no-slash -> slash 301 in docs/seo-edge-rules.md is a
 * hand-written copy of `isSlashedPath` across every locale. It lives in a
 * dashboard, not this repo, so the doc is the source a human pastes from, and
 * this test keeps it honest. A new locale or a new `trailingSlash = 'always'`
 * route fails here until the doc's expression is updated (and then the rule
 * in Cloudflare with it). Otherwise that route's no-slash URLs answer 404.
 */
const FRONTEND = resolve(process.cwd());
const DOC = readFileSync(join(FRONTEND, '..', 'docs', 'seo-edge-rules.md'), 'utf8');
const LOCALES: string[] = JSON.parse(
	readFileSync(join(FRONTEND, 'project.inlang/settings.json'), 'utf8')
).locales;

const expression = /```\n(\(http\.host[\s\S]*?)\n```/.exec(DOC)?.[1] ?? '';
const indexSet = new Set(
	[.../in \{([^}]*)\}/.exec(expression)?.[1].matchAll(/"([^"]+)"/g) ?? []].map((m) => m[1])
);
const wildcards = [...expression.matchAll(/wildcard "([^"]+)"/g)].map((m) => m[1]);
const excludes = [...expression.matchAll(/not http\.request\.uri\.path contains "([^"]+)"/g)].map(
	(m) => m[1]
);

/** Cloudflare's `wildcard`: `*` matches any run of characters, slashes included. */
const wildcard = (pattern: string, path: string) =>
	new RegExp(
		`^${pattern
			.split('*')
			.map((part) => part.replace(/[.+?^${}()|[\]\\]/g, '\\$&'))
			.join('.*')}$`,
		'i'
	).test(path);

/** The documented rule, evaluated for a path on ochorus.com. */
function edgeRedirects(path: string): boolean {
	if (path.endsWith('/') || excludes.some((x) => path.includes(x))) return false;
	return indexSet.has(path) || wildcards.some((w) => wildcard(w, path));
}

/** A concrete path for every page route, params filled in, in every locale. */
function samplePaths(): string[] {
	const ids: string[] = [];
	const walk = (dir: string, url: string[]) => {
		for (const e of readdirSync(dir, { withFileTypes: true })) {
			if (e.isDirectory()) {
				if (!e.name.startsWith('(')) walk(join(dir, e.name), [...url, e.name.replace(/^\[.*\]$/, 'x')]);
			} else if (e.name === '+page.svelte') ids.push(`/${url.join('/')}`);
		}
	};
	walk(join(FRONTEND, 'src', 'routes'), []);
	const extra = ['/books/x/cover.jpg', '/wp-content/uploads/a.pdf', '/biographies/era', '/feed.xml'];
	return LOCALES.flatMap((l) =>
		[...ids, ...extra].map((p) => (l === 'en' ? p : `/${l}${p === '/' ? '' : p}`))
	);
}

describe('docs/seo-edge-rules.md', () => {
	it('parses the documented expression', () => {
		expect(expression, 'no ```(http.host …``` block found').toContain('http.host eq "ochorus.com"');
		expect(indexSet.size).toBeGreaterThan(10);
		expect(wildcards.length).toBeGreaterThan(10);
	});

	it('301s exactly the no-slash paths the app itself treats as slashed', () => {
		const paths = samplePaths();
		expect(paths.length).toBeGreaterThan(100);
		const wrong = paths
			.filter((p) => p !== '/' && !p.endsWith('/'))
			.filter((p) => edgeRedirects(p) !== isSlashedPath(p))
			.map((p) => `${p}: edge ${edgeRedirects(p) ? 'redirects' : 'passes'}, app says ${isSlashedPath(p) ? 'slashed' : 'not slashed'}`);
		expect(wrong).toEqual([]);
	});
});
