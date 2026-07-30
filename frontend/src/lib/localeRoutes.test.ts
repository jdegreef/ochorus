import { existsSync, readFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

/**
 * Every configured UI locale must have its index-page rewrites in render.yaml.
 *
 * Render's route matcher has no wildcard for the locale segment, so each locale
 * repeats the same block. That list is hand-maintained and drifted twice: /pt
 * and /ar were both wired as full locales — message catalogs, locale registry,
 * sitemap entries — while render.yaml still only knew es/sw/lg. The pages were
 * built and sitemapped, and every one of them served the 4 KB SPA shell to
 * crawlers. 166 Portuguese URLs were advertised to Google that way.
 *
 * Nothing else catches it: the build succeeds, the tests pass, the pages exist
 * on disk, and the only symptom is a 4 KB response to a crawler nobody watches.
 */
const ROOT = [resolve(process.cwd(), '..'), resolve(process.cwd())].find((d) =>
	existsSync(join(d, 'render.yaml'))
) as string;
const FRONTEND = [resolve(process.cwd()), resolve(process.cwd(), 'frontend')].find((d) =>
	existsSync(join(d, 'project.inlang/settings.json'))
) as string;

const RENDER_YAML = readFileSync(join(ROOT, 'render.yaml'), 'utf8');
const LOCALES: string[] = JSON.parse(
	readFileSync(join(FRONTEND, 'project.inlang/settings.json'), 'utf8')
).locales.filter((l: string) => l !== 'en');

/** Prerendered index pages that need an explicit rewrite per locale. */
const INDEX_PAGES = ['books', 'biographies', 'about', 'contact', 'legal', 'sermons', 'plans', 'topics'];

describe('render.yaml locale routes', () => {
	it('covers every configured locale', () => {
		const missing = LOCALES.filter((l) => !RENDER_YAML.includes(`source: /${l}\n`));
		expect(missing, 'locales with no landing-page rewrite').toEqual([]);
	});

	for (const page of INDEX_PAGES) {
		it(`covers /<locale>/${page} for every locale`, () => {
			const missing = LOCALES.filter((l) => !RENDER_YAML.includes(`source: /${l}/${page}\n`));
			expect(missing, `locales missing /${page}`).toEqual([]);
		});
	}

	it('rewrites every locale to its own .html, never another locale’s', () => {
		for (const l of LOCALES) {
			const re = new RegExp(`source: /${l}(/[a-z-]+)?\\n\\s*destination: (/[^\\n]+)`, 'g');
			for (const m of RENDER_YAML.matchAll(re)) {
				expect(m[2], `source /${l}${m[1] ?? ''}`).toMatch(new RegExp(`^/${l}[./]`));
			}
		}
	});
});
