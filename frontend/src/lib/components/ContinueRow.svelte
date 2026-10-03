<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { EmblemName } from '$lib/emblems';
	import Emblem from './Emblem.svelte';

	/**
	 * One thing the reader is partway through, as a resume row inside a
	 * `<ContinueShelf>`: a visual (cover, emblem), the title, how far they are
	 * (a meter plus its words), and the one verb. The whole row is the link, so
	 * the verb is drawn as a button, not a second control.
	 */
	let {
		href,
		title,
		lang,
		visual,
		emblem,
		progress,
		caption,
		verb,
		hue
	}: {
		href: string;
		title: string;
		/** The title's language, when it is content in another language. */
		lang?: string;
		/** A cover or other visual; or pass `emblem` for the curated emblem chip. */
		visual?: Snippet;
		emblem?: EmblemName;
		/** The meter — `<ProgressBar>`, or a series' `<SeriesSegments>`. */
		progress: Snippet;
		/** How far, in words ("Chapter 4 of 31", "Day 6 of 31"). */
		caption: string;
		verb: string;
		/** The emblem chip's accent. */
		hue?: string;
	} = $props();
</script>

<li>
	<a class="continue-row card-tint" style={hue ? `--shelf-hue: ${hue}` : undefined} {href}>
		{#if visual}
			{@render visual()}
		{:else if emblem}
			<span class="emblem-chip continue-chip"><Emblem name={emblem} /></span>
		{/if}
		<span class="flex min-w-0 flex-1 flex-col gap-1.5">
			<span class="continue-title truncate" {lang} dir="auto">{title}</span>
			{@render progress()}
			<span class="text-small text-muted">{caption}</span>
		</span>
		<span class="btn btn-sm btn-primary shrink-0">{verb}</span>
	</a>
</li>

<style>
	.continue-row {
		display: flex;
		align-items: center;
		gap: 0.85rem;
		height: 100%;
		padding: 0.85rem 1rem;
		border: 1px solid var(--border);
		border-radius: var(--radius-card);
		background: var(--surface);
		color: inherit;
		text-decoration: none;
	}
	.continue-chip {
		--chip-size: 2.75rem;
		--chip-hue: var(--shelf-hue);
	}
	.continue-title {
		font-family: var(--font-display);
		font-weight: 600;
		color: var(--text);
	}
</style>
