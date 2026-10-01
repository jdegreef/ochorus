<script lang="ts">
	/**
	 * A two-line mark inside the shared .emblem-chip: a small label over a large
	 * value — "MAT" over 11 for a sermon's passage (SermonMonogram), "DAYS" over
	 * 21 for a plan, "BOOKS" over 4 for a series. Tinted by `--chip-hue`
	 * (inherited, or `hue`). Decorative — every caller names the thing beside
	 * it — so it is aria-hidden.
	 *
	 * A larger chip raises `--monogram-size` to a bigger scale step (the sermon
	 * plate uses --fs-h2); the default is --fs-h3.
	 */
	let {
		top = '',
		value = '',
		hue,
		class: klass = ''
	}: {
		/** The small line; upper-cased where the script has case. */
		top?: string;
		/** The large line — a chapter, a count, or a lone initial. */
		value?: string;
		/** Sets `--chip-hue` here rather than inheriting it. */
		hue?: string;
		class?: string;
	} = $props();

	const label = $derived(top.toUpperCase());
	// Tracking suits cased capitals; in Arabic, Devanagari or Ethiopic it pulls
	// joined letters apart — and those scripts have no case.
	const spaced = $derived(label !== label.toLowerCase());
</script>

<span
	class="monogram emblem-chip {klass}"
	style={hue ? `--chip-hue: ${hue}` : undefined}
	aria-hidden="true"
>
	{#if label}<span class="top" class:spaced>{label}</span>{/if}
	{#if value}<span class="value">{value}</span>{/if}
</span>

<style>
	.monogram {
		--chip-ring: 1.5px;
		--chip-ring-mix: 45%;
		flex-direction: column;
		gap: 0.1rem;
		color: color-mix(in srgb, var(--chip-hue) 55%, var(--color-text));
		/* One glyph sized from the scale; the label is a fixed fraction of it
		   (em, as typeScaleGuard sanctions) so the widest sermon book —
		   "1 कुरिन्थि" — stays inside the circle at every breakpoint. */
		font-size: var(--monogram-size, var(--fs-h3));
		line-height: 1;
		white-space: nowrap;
	}
	.top {
		font-family: var(--font-sans);
		font-size: 0.45em;
		font-weight: 600;
	}
	.top.spaced {
		letter-spacing: 0.1em;
	}
	.value {
		font-family: var(--font-display);
		font-weight: 600;
		font-variant-numeric: lining-nums;
	}
</style>
