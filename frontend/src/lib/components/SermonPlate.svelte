<script lang="ts">
	import type { Snippet } from 'svelte';
	import Emblem from '$lib/components/Emblem.svelte';
	import { emblemForSermon, emblemHue } from '$lib/emblems';
	import { tintable } from '$lib/coverArt';

	/**
	 * A sermon's plate: the hue-washed band it wears at the head of its own page
	 * and in the Sermon of the week panel. The sermon's words sit in the band and
	 * its emblem anchors the far end — the same composition as its share card, so
	 * a reader who arrived from a forwarded link recognises where they landed.
	 *
	 * WHY A BAND AND NOT A COVER
	 * Sermons had art everywhere except where it counted — a 48px chip on the
	 * shelves, nothing at all on the sermon page, which opened as a wall of type.
	 * The obvious fix, "give sermons covers like books have", is the wrong one: a
	 * 3:4 portrait plate says *volume*, and a sermon is a twenty-minute read. On
	 * a mixed shelf the differing silhouette is the one instant cue telling a
	 * reader which is which, and matching it throws that away.
	 *
	 * An earlier draft put a decorative band ABOVE the title with the emblem
	 * centred in it. It read as an empty box: a wide wash with one small chip
	 * adrift in it and the real content still below. Wrapping the header instead
	 * gives the wash something to hold.
	 *
	 * THE HUE IS THE EMBLEM'S OWN
	 * Derived from the art (`emblemHue`), not authored: a new sermon is coloured
	 * the moment its emblem is picked. It reaches the pixel only through
	 * color-mix (STYLE_GUIDE §Cards), so a saturated accent stays legible in both
	 * themes and never sets type.
	 *
	 * `tintable` first, because a wash is only as visible as the hue is light:
	 * the raven emblem's slate is dark enough that 9% of it over a dark surface
	 * showed nothing at all, leaving one sermon in the library looking as though
	 * the plate had failed to load.
	 *
	 * Not used on the sermons index: those rows tint from the PREACHER'S ERA
	 * (`--row-hue`), a deliberate documented choice that makes a shelf sorted by
	 * era read as a timeline. This is a different job — one sermon at a time.
	 */
	let {
		slug,
		chip = '4.5rem',
		children
	}: {
		slug: string;
		/** Diameter of the emblem chip. The panel wants a smaller one. */
		chip?: string;
		/** The sermon's own header — eyebrow, title, byline. */
		children: Snippet;
	} = $props();

	const emblem = $derived(emblemForSermon(slug));
	const hue = $derived(tintable(emblemHue(emblem)));
</script>

<div class="sermon-plate hue-band" style="--band-hue: {hue}; --chip-size: {chip}; --chip-hue: {hue}">
	<div class="min-w-0 flex-1">{@render children()}</div>
	<!-- Decorative: every caller names the sermon in the band beside it, so
	     labelling the emblem would have a screen reader say it twice. -->
	<span class="emblem-chip" aria-hidden="true"><Emblem name={emblem} /></span>
</div>

<style>
	.sermon-plate {
		display: flex;
		align-items: center;
		gap: 1.25rem;
		padding: 1.15rem 1.35rem;
		border-radius: var(--radius-card);
		/* `.hue-band` ends in a hairline at its foot, which is what a card's band
		   needs above a body. A plate is free-standing, so it closes the box. */
		border: 1px solid color-mix(in srgb, var(--band-hue) 22%, var(--border));
	}
	/* Narrow phones: the chip costs a third of the measure, and the title is
	   what the reader came for. */
	@media (max-width: 24rem) {
		.sermon-plate > :global(.emblem-chip) {
			display: none;
		}
	}
</style>
