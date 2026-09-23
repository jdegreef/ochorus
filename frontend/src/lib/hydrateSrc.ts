/**
 * Keep a data-driven `<img>`'s `src`/`srcset` on the data, including at
 * hydration — which Svelte, on purpose, does not do.
 *
 * While hydrating, Svelte 5 repairs every attribute of a prerendered element
 * EXCEPT `src` and `srcset`: resetting them would refetch, so it assumes the
 * server got them right (`set_attribute` returns early). On a prerendered page
 * that assumption breaks whenever the data moved between the build and the
 * visit — a book published, an author's count changing their place in a
 * sorted grid, a photo replaced. The card then gets the NEW item's name, link
 * and overlay over the OLD item's picture: the home shelf showed paintings with
 * no title, and one book's title drawn across another's designed cover.
 *
 * Worse, Svelte records the stale server value as what it last wrote, so a
 * later update that happens to equal it is skipped as "unchanged". So this
 * action re-applies on EVERY update, not just once on attach: the DOM, not
 * Svelte's cache, is what it compares against.
 *
 * `srcset` goes first: with a stale `srcset` still present, the browser picks
 * its candidate over the new `src` and the old picture stays.
 *
 * Usage: `<img src={url} srcset={set} use:hydrateSrc={{ src: url, srcset: set }} />`.
 * Keep the plain attributes too — they are what the prerendered HTML carries.
 * An empty `src` is left alone: the markup decides what a missing image means.
 */
export interface ImgSource {
	src: string | null | undefined;
	srcset?: string | null | undefined;
}

export function hydrateSrc(img: HTMLImageElement, source: ImgSource) {
	const apply = ({ src, srcset }: ImgSource) => {
		if (!src) return;
		if ((img.getAttribute('srcset') ?? '') !== (srcset ?? '')) {
			if (srcset) img.setAttribute('srcset', srcset);
			else img.removeAttribute('srcset');
		}
		if (img.getAttribute('src') !== src) img.setAttribute('src', src);
	};
	apply(source);
	return { update: apply };
}
