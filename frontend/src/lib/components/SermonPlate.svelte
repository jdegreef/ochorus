<script lang="ts">
	import type { Snippet } from 'svelte';
	import { emblemForSermon } from '$lib/emblemNames';
	import { EMBLEM_HUES } from '$lib/emblemHues';
	import { tintable } from '$lib/coverArt';

	/**
	 * A sermon's plate: the hue-washed band it wears at the head of its own page
	 * and in the Sermon of the week panel. The sermon's words sit in the band and
	 * its emblem anchors the far end — the same composition as its share card
	 * (`scripts/generate-sermon-og.mjs`), so a reader arriving from a forwarded
	 * link recognises where they landed.
	 *
	 * The design rules it follows — why a sermon gets a landscape band and not a
	 * 3:4 cover, and why a shelf tints by the shelf's sort while an item standing
	 * alone tints from its own art — are STYLE_GUIDE §Cards'.
	 *
	 * Two things worth knowing at the call site:
	 *
	 *   - The hue is derived from the art, never authored, so a new sermon is
	 *     coloured the moment its emblem is picked; `tintable` then lifts it into
	 *     a range a 9% wash can actually show. It comes from the precomputed
	 *     `EMBLEM_HUES` rather than from `emblemHue()`, and the DRAWING is
	 *     imported dynamically — between them that keeps 51 emblems' worth of
	 *     SVG (10.6 KB gzip, measured) off the critical path of the home page
	 *     and every sermon page, which is what a static `Emblem` import cost.
	 *     The band paints from the map immediately; the art arrives after
	 *     hydration, and it is decorative, so nobody waits on it.
	 *   - It renders a band, not a link. One of its two callers wraps it in an
	 *     anchor and owns the hover state, since heading a page is the commoner
	 *     job and a plate should not assume it is clickable.
	 */
	let {
		slug,
		compact = false,
		children
	}: {
		slug: string;
		/**
		 * Smaller chip and tighter band, for the Sermon of the week panel — it
		 * sits inside a page column rather than heading one.
		 *
		 * A variant, not a CSS length: the size has to come from the stylesheet
		 * so the phone rule below can reach it. Handed in as an inline
		 * `--chip-size` (as it was at first) it beats every rule in the sheet
		 * whatever the media query says, and the phone rule silently does
		 * nothing — measured, not assumed.
		 */
		compact?: boolean;
		/** The sermon's own header — eyebrow, title, byline. */
		children: Snippet;
	} = $props();

	const emblem = $derived(emblemForSermon(slug));
	const hue = $derived(tintable(EMBLEM_HUES[emblem]));
</script>

<div
	class="sermon-plate hue-band"
	class:compact
	style="--band-hue: {hue}; --chip-hue: {hue}"
>
	<div class="min-w-0 flex-1">{@render children()}</div>
	<!-- Decorative: every caller names the sermon in the band beside it, so
	     labelling the emblem would have a screen reader say it twice. Emblem
	     hides itself when given no `label`, as at every other chip call site.
	     The chip keeps its size and tint while the art loads, so nothing
	     reflows when it arrives. -->
	<span class="emblem-chip">
		{#await import('$lib/components/Emblem.svelte') then Loaded}
			<Loaded.default name={emblem} />
		{/await}
	</span>
</div>

<style>
	.sermon-plate {
		--chip-size: 4.5rem;
		display: flex;
		align-items: center;
		gap: 1.25rem;
		padding: 1.15rem 1.35rem;
		border-radius: var(--radius-card);
		/* `.hue-band` ends in a hairline at its foot, which is what a card's band
		   needs above a body. A plate is free-standing, so it closes the box —
		   with the band's own line, not a second copy of the mix. */
		border: 1px solid var(--band-line);
	}
	.sermon-plate.compact {
		--chip-size: 3.5rem;
		gap: 1rem;
		padding: 1rem 1.15rem;
	}
	/* Phones. At full size the chip eats a third of a 390px measure and pushed
	   the longest title to four lines, so it shrinks — but it does NOT go away:
	   a sermon wearing its art on a phone is the whole point of the plate, and
	   the phone is where most of this library is read.

	   `.compact` is listed too: it is the more specific selector, so a bare
	   `.sermon-plate` here would lose to it and the panel would keep its
	   full-size chip on a phone. */
	@media (max-width: 30rem) {
		.sermon-plate,
		.sermon-plate.compact {
			--chip-size: 3rem;
			gap: 0.9rem;
			padding: 1rem 1.05rem;
		}
	}
</style>
