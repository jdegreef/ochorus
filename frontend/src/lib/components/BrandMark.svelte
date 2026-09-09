<script lang="ts">
	// The real Ochorus logo — the open book with a quill, and the "Ochorus"
	// wordmark built into the artwork, exactly as it appears on the ministry's
	// printed books.
	//
	// Rendered as a <use> of the shared <symbol> that BrandSprite defines once
	// per document (see $lib/brand/lockup). It used to inline the whole ~4.3 KB
	// SVG on every instance via {@html}; the book shelf renders one per cover, so
	// /books carried 85 copies (~365 KB). <use> keeps the mark inline — so
	// `fill="currentColor"` still resolves against the surrounding text colour,
	// one mark for both themes — while the geometry is paid for once.
	//
	// The <span> wrapper and the single child <svg> are kept deliberately: the
	// share-card renderer (coverCardMarkup) inlines the full lockup into the same
	// `<span class="brandmark">…<svg>…</svg>`, and coverMarkupParity holds the two
	// trees against each other (it abstracts the mark to "one svg inside", so a
	// <use> here and inline paths there stay pixel-equal and in parity). The
	// canonical artwork lives in the backend and is mirrored to $lib/brand;
	// `brandAssets.test.ts` fails if the two drift apart.
	import { LOCKUP_SYMBOL_ID, LOCKUP_VIEWBOX } from '$lib/brand/lockup';

	// Height; the lockup is ~1.66:1 so width follows. A bare number means px, and
	// 36 is the header default — at the old 24px mark size the built-in wordmark
	// is too small to read. A string is any CSS length, which is how the book
	// cover plate asks for a height in container units so the mark scales with
	// the card.
	let { height = 36 }: { height?: number | string } = $props();
	const size = $derived(typeof height === 'number' ? `${height}px` : height);
</script>

<span class="brandmark" style="--h: {size}" role="img" aria-label="Ochorus">
	<svg class="brandmark-svg" viewBox={LOCKUP_VIEWBOX} aria-hidden="true">
		<use href="#{LOCKUP_SYMBOL_ID}" />
	</svg>
</span>

<style>
	.brandmark {
		/* Just a host for the <svg> — the anchor around it already handles
		   alignment. */
		display: inline-block;
	}
	.brandmark svg {
		height: var(--h);
		width: auto;
		display: block;
		/* The symbol paints in currentColor; anchor it here so the mark follows
		   the surrounding text in both themes. */
		fill: currentColor;
	}
</style>
