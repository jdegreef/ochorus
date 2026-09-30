<script lang="ts">
	import { sermonMonogram } from '$lib/sermonMonogram';

	/**
	 * A sermon's mark on a shelf: its passage as a monogram (MAT over 11) inside
	 * the shared .emblem-chip, tinted by the chip's `--chip-hue`. Decorative —
	 * the full passage is always printed beside it — so it is aria-hidden. A
	 * sermon with no passage wears its title's first letter, set the same way.
	 */
	let {
		scriptureRef,
		title,
		class: klass = ''
	}: { scriptureRef: string | null | undefined; title: string; class?: string } = $props();

	const mark = $derived(sermonMonogram(scriptureRef, title));
	// Tracking suits cased capitals; in Arabic, Devanagari or Ethiopic it pulls
	// joined letters apart — and those scripts have no case.
	const spaced = $derived(mark.book !== mark.book.toLocaleLowerCase());
</script>

<span class="sermon-monogram emblem-chip {klass}" aria-hidden="true">
	{#if mark.book}<span class="book" class:spaced>{mark.book}</span>{/if}
	{#if mark.chapter}<span class="chapter">{mark.chapter}</span>{/if}
</span>

<style>
	.sermon-monogram {
		--chip-ring: 1.5px;
		--chip-ring-mix: 45%;
		flex-direction: column;
		gap: 0.1rem;
		color: color-mix(in srgb, var(--chip-hue) 55%, var(--color-text));
		/* The monogram is one glyph sized from the scale; the book line is a
		   fixed fraction of it (em, as typeScaleGuard sanctions) so the widest
		   book — "1 कुरिन्थि" — stays inside the circle at every breakpoint. */
		font-size: var(--fs-h3);
		line-height: 1;
		white-space: nowrap;
	}
	.book {
		font-family: var(--font-sans);
		font-size: 0.45em;
		font-weight: 600;
	}
	.book.spaced {
		letter-spacing: 0.1em;
	}
	.chapter {
		font-family: var(--font-display);
		font-weight: 600;
		font-variant-numeric: lining-nums;
	}
</style>
