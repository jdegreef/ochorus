import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';
import { describe, expect, it } from 'vitest';
import { hydrateSrc } from './hydrateSrc';

/**
 * Svelte 5 keeps a prerendered `<img>`'s `src`/`srcset` while hydrating, and
 * remembers the stale value as its own. These are the two ways that showed a
 * reader the wrong picture, driven directly on the DOM the hydration leaves.
 */
const prerendered = (src: string, srcset?: string) => {
	const img = document.createElement('img');
	img.setAttribute('src', src);
	if (srcset) img.setAttribute('srcset', srcset);
	return img;
};

describe('hydrateSrc', () => {
	it('repoints an image the HTML prerendered for another item', () => {
		const img = prerendered('/covers/old.jpg', '/covers/old-320.webp 320w');
		hydrateSrc(img, { src: '/covers/art/new.jpg', srcset: '/covers/art/new-320.webp 320w' });
		expect(img.getAttribute('src')).toBe('/covers/art/new.jpg');
		expect(img.getAttribute('srcset')).toBe('/covers/art/new-320.webp 320w');
	});

	it('drops a stale srcset the new image does not have', () => {
		// Left in place, the browser would pick the old candidate over `src`.
		const img = prerendered('/covers/old.jpg', '/covers/old-320.webp 320w');
		hydrateSrc(img, { src: '/portraits/new.jpg' });
		expect(img.hasAttribute('srcset')).toBe(false);
		expect(img.getAttribute('src')).toBe('/portraits/new.jpg');
	});

	it('re-applies on update even when the value equals the stale one', () => {
		// Svelte's cache still says "old" after the repair, so an update back to
		// "old" is skipped by Svelte — the action has to write it itself.
		const img = prerendered('/covers/old.jpg');
		const action = hydrateSrc(img, { src: '/covers/new.jpg' });
		action.update({ src: '/covers/old.jpg' });
		expect(img.getAttribute('src')).toBe('/covers/old.jpg');
	});

	it('leaves a matching image, and a missing source, alone', () => {
		const img = prerendered('/covers/same.jpg', '/covers/same-320.webp 320w');
		hydrateSrc(img, { src: '/covers/same.jpg', srcset: '/covers/same-320.webp 320w' });
		expect(img.getAttribute('src')).toBe('/covers/same.jpg');
		hydrateSrc(img, { src: '' });
		expect(img.getAttribute('src')).toBe('/covers/same.jpg');
	});
});

/**
 * The action only protects the images that wear it, and forgetting it is
 * invisible: the page looks right until the data behind a prerendered list
 * drifts, and then a card shows one item's picture under another's name. So,
 * like rtl.test.ts, this is a source-text check: every `<img>` whose source
 * comes from data — an expression, an interpolated string or a spread — must
 * carry `use:hydrateSrc`.
 *
 * One named exception: BookCover's `whenComplete`, which calls `hydrateSrc`
 * itself — it has to repoint before it measures, in ONE action, so the order
 * cannot depend on how Svelte attaches two.
 */
describe('every data-driven <img> keeps its src on its data', () => {
	const SRC = join(process.cwd(), 'src');
	const svelteFiles = (dir: string, out: string[] = []): string[] => {
		for (const name of readdirSync(dir)) {
			const path = join(dir, name);
			if (statSync(path).isDirectory()) {
				if (name !== 'paraglide') svelteFiles(path, out);
			} else if (name.endsWith('.svelte')) out.push(path);
		}
		return out;
	};

	it('wears use:hydrateSrc', () => {
		const missing: string[] = [];
		for (const path of svelteFiles(SRC)) {
			const text = readFileSync(path, 'utf8');
			// `<img ` to its self-closing `/>` — an `=>` inside a handler does not
			// end the tag, which a bare `>` would; the space skips prose mentions
			// of `<img>` in comments.
			for (const m of text.matchAll(/<img\s[\s\S]*?\/>/g)) {
				const tag = m[0];
				// Data-driven in any spelling: `src={x}`, the `{src}` shorthand, an
				// interpolated string (`src="/covers/{slug}.jpg"`), or attributes
				// spread in whole. Only a literal path with no `{` in it is exempt.
				const dataDriven =
					/\s(?:src|srcset)=\{/.test(tag) ||
					/\s\{(?:src|srcset)\}/.test(tag) ||
					/\s(?:src|srcset)="[^"]*\{/.test(tag) ||
					/\{\s*\.\.\./.test(tag);
				if (!dataDriven) continue;
				if (/use:hydrateSrc\b/.test(tag)) continue;
				if (path.endsWith('BookCover.svelte') && /use:whenComplete\b/.test(tag)) continue;
				const line = text.slice(0, m.index).split('\n').length;
				missing.push(`${relative(SRC, path)}:${line}`);
			}
		}
		expect(missing).toEqual([]);
	});
});
