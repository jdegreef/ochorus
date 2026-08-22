<script lang="ts">
	// The real Ochorus logo — the open book with a quill, and the "Ochorus"
	// wordmark built into the artwork, exactly as it appears on the ministry's
	// printed books.
	//
	// This replaces a hand-drawn approximation that had the quill pointing the
	// WRONG WAY (up-left, symmetric book) and existed as two divergent copies:
	// one here and one inlined in backend/library/covers.py. The canonical file
	// now lives in the backend (its Docker image ships `backend/` only, so
	// covers.py cannot read anything under frontend/) and is mirrored here;
	// `brandAssets.test.ts` fails if the two drift apart.
	//
	// Inlined via `?raw` rather than <img src> so `fill="currentColor"` resolves
	// against the surrounding text colour — one file serves both themes.
	import lockup from '$lib/brand/ochorus-lockup.svg?raw';

	// Height; the lockup is ~1.66:1 so width follows. A bare number means px, and
	// 36 is the header default — at the old 24px mark size the built-in wordmark
	// is too small to read. A string is any CSS length, which is how the book
	// cover plate asks for a height in container units so the mark scales with
	// the card.
	let { height = 36 }: { height?: number | string } = $props();
	const size = $derived(typeof height === 'number' ? `${height}px` : height);
</script>

<span class="brandmark" style="--h: {size}" role="img" aria-label="Ochorus">
	<!-- eslint-disable-next-line svelte/no-at-html-tags -- our own build-time asset -->
	{@html lockup}
</span>

<style>
	.brandmark {
		/* Just a host for the inlined <svg> — the anchor around it already
		   handles alignment. */
		display: inline-block;
	}
	.brandmark :global(svg) {
		height: var(--h);
		width: auto;
		display: block;
	}
</style>
