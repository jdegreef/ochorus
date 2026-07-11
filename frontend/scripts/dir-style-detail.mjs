// Reshape prerendered DETAIL pages to directory-style, per locale:
//   build/books/<slug>.html  ->  build/books/<slug>/index.html
//
// Why: the static host (Render) can't map a missing `/books/:slug` to a 404
// page — a `:slug -> :slug.html` rewrite serves a blank empty-200 when the file
// is absent (unpublished/unknown slug), and does NOT fall back to 404.html
// (deploy skill, gotcha #8). With detail pages as directory indexes, the host
// serves a real book from `<slug>/index.html` natively — so render.yaml drops
// the per-slug rewrites, and a MISSING slug matches no rule and falls through to
// the `/* -> /200.html` SPA catch-all, which renders the designed not-found page.
//
// Only single-segment detail slugs move. List pages (build/books.html) live one
// level up and are untouched; the reader (/books/:slug/:order) isn't prerendered.
import { readdirSync, mkdirSync, renameSync, existsSync, statSync } from 'node:fs';
import { join } from 'node:path';

const BUILD = 'build';
const LOCALES = ['', 'es', 'sw', 'lg'];
const TYPES = ['books', 'authors', 'sermons', 'plans'];

let moved = 0;
for (const loc of LOCALES) {
	for (const type of TYPES) {
		const dir = loc ? join(BUILD, loc, type) : join(BUILD, type);
		if (!existsSync(dir)) continue;
		for (const name of readdirSync(dir)) {
			if (!name.endsWith('.html')) continue;
			const src = join(dir, name);
			if (statSync(src).isDirectory()) continue;
			const slug = name.slice(0, -'.html'.length);
			const destDir = join(dir, slug);
			mkdirSync(destDir, { recursive: true });
			renameSync(src, join(destDir, 'index.html'));
			moved++;
		}
	}
}
console.log(`dir-style: reshaped ${moved} detail pages to <slug>/index.html`);
