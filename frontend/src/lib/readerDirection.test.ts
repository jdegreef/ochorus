import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const FRONTEND = join(dirname(fileURLToPath(import.meta.url)), '..', '..');

/**
 * `dir="auto"` must sit on the CONTENT, never on the container that also holds
 * localized chrome.
 *
 * The readers mix two directions: breadcrumbs and prev/next follow the UI
 * locale, while the chapter text follows the language the text is actually in.
 * When `dir="auto"` sat on the outer <article>, it resolved from the first
 * strong character in that element — the localized breadcrumb. Under /ar that
 * is Arabic, so English book text inherited RTL and sentence-final punctuation
 * rendered at the start of the line (".and defects await the creature").
 *
 * This was invisible until Arabic shipped: with only LTR locales, resolving
 * from the chrome and resolving from the content give the same answer. It will
 * be equally invisible if it regresses, so it is pinned here rather than left
 * to a browser check nobody repeats.
 */
const READERS = [
	'src/routes/books/[slug]/[order]/+page.svelte',
	'src/routes/sermons/[slug]/+page.svelte'
];

describe('reader text direction', () => {
	for (const path of READERS) {
		const src = readFileSync(join(FRONTEND, path), 'utf8');

		it(`${path}: <article> does not carry dir`, () => {
			const article = src.match(/<article[^>]*>/s)?.[0] ?? '';
			expect(article).not.toMatch(/\bdir=/);
		});

		it(`${path}: the title and body carry dir="auto"`, () => {
			const title = src.match(/<h1[^>]*>\{(?:chapter|sermon)\.title\}/s)?.[0] ?? '';
			expect(title, 'chapter/sermon title').toMatch(/dir="auto"/);

			const body = src.match(/<div class="reading"[^>]*>/s)?.[0] ?? '';
			expect(body, 'reading body').toMatch(/dir="auto"/);
		});
	}
});
