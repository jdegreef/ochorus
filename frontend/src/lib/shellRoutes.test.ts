import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import { SHELL_ROUTES, isShellPath } from './shellRoutes';

/**
 * The 200-shell rewrites in render.yaml, $lib/shellRoutes and the route tree
 * must agree. There is no catch-all any more: a client-only route missing from
 * render.yaml still renders for a reader (Render's 404.html is the same shell),
 * but answers 404 — invisible until a monitor, the PWA or a support report
 * trips over it. So the drift is caught here instead.
 */
const FRONTEND = resolve(process.cwd());
const RENDER_YAML = readFileSync(join(FRONTEND, '..', 'render.yaml'), 'utf8');
const LOCALES: string[] = JSON.parse(
	readFileSync(join(FRONTEND, 'project.inlang/settings.json'), 'utf8')
).locales;
const ROUTES = join(FRONTEND, 'src', 'routes');

/** Route ids (`/admin/users/[uid]`) whose +page.ts opts out of prerendering. */
function clientOnlyRoutes(dir = ROUTES, id = ''): string[] {
	const out: string[] = [];
	for (const name of readdirSync(dir)) {
		const full = join(dir, name);
		if (statSync(full).isDirectory()) out.push(...clientOnlyRoutes(full, `${id}/${name}`));
		else if (name === '+page.ts' && /export const prerender\s*=\s*false/.test(readFileSync(full, 'utf8')))
			out.push(id || '/');
	}
	return out;
}

describe('SPA shell routes', () => {
	it('covers every client-only route', () => {
		const routes = clientOnlyRoutes();
		expect(routes.length, 'the route walk found nothing — did src/routes move?').toBeGreaterThan(5);
		// A concrete path for each id: a param segment stands in as a sample value.
		const missing = routes.filter((id) => !isShellPath(id.replace(/\[[^\]]+\]/g, 'x')));
		expect(missing, 'client-only routes that would answer 404').toEqual([]);
	});

	it('rewrites each shell route to 200.html, bare and under /:lang', () => {
		// One `/:lang` rule stands for every non-English locale (a copy per locale
		// took the service past Render's route cap — see render.yaml).
		expect(LOCALES.length, 'no locales configured?').toBeGreaterThan(1);
		const missing: string[] = [];
		for (const prefix of ['', '/:lang']) {
			for (const r of SHELL_ROUTES) {
				const rule = `source: ${prefix}${r}\n        destination: /200.html\n`;
				if (!RENDER_YAML.includes(rule)) missing.push(`${prefix}${r}`);
			}
		}
		expect(missing).toEqual([]);
	});

	it('leaves real content paths to 404', () => {
		expect(isShellPath('/books/no-such-book/')).toBe(false);
		expect(isShellPath('/wp-content/uploads/x.pdf')).toBe(false);
		expect(isShellPath('/administrator')).toBe(false);
		expect(isShellPath('/admin')).toBe(true);
		expect(isShellPath('/admin/users/42/')).toBe(true);
		expect(isShellPath('/settings/')).toBe(true);
	});

	it('ships the 404 shell from postbuild', () => {
		const pkg = JSON.parse(readFileSync(join(FRONTEND, 'package.json'), 'utf8'));
		expect(pkg.scripts.postbuild).toContain('scripts/build-404.mjs');
		expect(existsSync(join(FRONTEND, 'scripts', 'build-404.mjs'))).toBe(true);
	});
});
