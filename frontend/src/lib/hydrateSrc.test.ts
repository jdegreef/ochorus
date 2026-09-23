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
