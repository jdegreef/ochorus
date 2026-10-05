<script lang="ts">
	import { hydrateSrc } from '$lib/hydrateSrc';
	import type { Snippet } from 'svelte';
	import { sermonArt } from '$lib/sermonArt';
	import SermonMonogram from '$lib/components/SermonMonogram.svelte';

	/**
	 * A sermon's plate: the hue-washed band it wears at the head of its own page
	 * and in the Sermon of the week panel. The sermon's words sit in the band and
	 * its passage monogram (MAT over 11, as on every sermon shelf) anchors the
	 * far end. Its share card (`scripts/generate-sermon-og.mjs`) keeps the same
	 * composition and hue, with the illustrated emblem in the chip.
	 *
	 * The design rules it follows — why a sermon gets a landscape band and not a
	 * 3:4 cover, and why a shelf tints by the shelf's sort while an item standing
	 * alone tints from its own art — are STYLE_GUIDE §Cards'.
	 *
	 * Two things worth knowing at the call site:
	 *
	 *   - The hue comes from `sermonArt`, shared with the topic fan and the
	 *     share card, so a sermon keeps one colour everywhere. No drawing is
	 *     loaded: the monogram is text, so it paints with the band.
	 *   - It renders a band, not a link. One of its two callers wraps it in an
	 *     anchor and owns the hover state, since heading a page is the commoner
	 *     job and a plate should not assume it is clickable.
	 */
	let {
		slug,
		scriptureRef,
		title,
		compact = false,
		portrait = null,
		children
	}: {
		slug: string;
		/** The passage and title the monogram is drawn from. */
		scriptureRef: string | null | undefined;
		title: string;
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
		/**
		 * An author portrait to stand in the chip in place of the monogram,
		 * so the preacher has a face — used by the Sermon of the week panel. Left
		 * null (the sermon's own page) keeps the monogram, so this is purely
		 * additive and the page header is unchanged. `pos` is the `object-position`
		 * from `$lib/portraits`, which lands the crop on the face; the face is
		 * printed as a duotone in the band's hue (`.duotone`, app.css).
		 */
		portrait?: { src: string; pos?: string } | null;
		/** The sermon's own header — eyebrow, title, byline. */
		children: Snippet;
	} = $props();

	const art = $derived(sermonArt(slug));
</script>

<div
	class="sermon-plate hue-band"
	class:compact
	style="--band-hue: {art.hue}; --chip-hue: {art.hue}"
>
	<div class="min-w-0 flex-1">{@render children()}</div>
	<!-- Decorative: every caller names the sermon in the band beside it, so
	     labelling the monogram — or the portrait that stands in for it — would
	     have a screen reader say it twice. SermonMonogram is aria-hidden; the
	     portrait carries an empty alt for the same reason. -->
	{#if portrait}
		<span class="emblem-chip portrait-chip duotone">
			<img src={portrait.src} use:hydrateSrc={{ src: portrait.src }} alt="" loading="lazy" style="object-position: {portrait.pos ?? '50% 0%'}" />
		</span>
	{:else}
		<SermonMonogram {scriptureRef} {title} />
	{/if}
</div>

<style>
	.sermon-plate {
		--chip-size: 4.5rem;
		--monogram-size: var(--fs-h2);
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
		--monogram-size: var(--fs-h3);
		gap: 1rem;
		padding: 1rem 1.15rem;
	}
	/* The portrait fills the chip the monogram otherwise sits in, printed in
	   the band's own hue (the shared .duotone recipe), so the face belongs to
	   the plate rather than sitting on it as a grey cutting. */
	.portrait-chip {
		--duotone-hue: var(--chip-hue);
	}
	.portrait-chip img {
		width: 100%;
		height: 100%;
		object-fit: cover;
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
			--monogram-size: var(--fs-h3);
			gap: 0.9rem;
			padding: 1rem 1.05rem;
		}
	}
</style>
