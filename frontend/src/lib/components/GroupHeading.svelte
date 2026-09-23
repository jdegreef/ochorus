<script lang="ts">
	import { hydrateSrc } from '$lib/hydrateSrc';
	import type { Snippet } from 'svelte';
	import { PORTRAIT_POSITION_DEFAULT, portraitSrcset } from '$lib/portraits';

	/**
	 * The heading over one group of a grouped browse shelf — Books by author,
	 * Sermons by preacher, Biographies by era, and a search-result group. These
	 * had drifted into four hand-rolled recipes (plain text, portrait + link, a
	 * sticky bordered bar, and a `.section-label`); this is the sermons recipe,
	 * once. Size is `.text-h3` (a group is a titled sub-section, not a page
	 * title); the count rides the shared `.count` class (tabular figures + muted).
	 *
	 * NOT `<SectionHeader>` — that is the home page's `.text-h2` "shelf title +
	 * See all" row, a different pattern.
	 *
	 * Two variants. The default is muted ink with the count sitting inline after
	 * the name. `sticky` is the Biographies era heading: it pins under the page's
	 * controls bar (via `--pinned-offset`), so it wears solid ink to read over
	 * the writers scrolling past behind it, a bottom border, and pushes the count
	 * to the far end. The caller owns the `<section>` wrapper (its `id` and
	 * `scroll-margin-top`); this owns the `<h2>`.
	 */
	let {
		name,
		href,
		portraitUrl,
		portraitPosition = PORTRAIT_POSITION_DEFAULT,
		count,
		as = 'h2',
		sticky = false,
		detail
	}: {
		name: string;
		/** Localized href — render the name as a link when present. */
		href?: string;
		/** 32px author portrait, shown before the name. */
		portraitUrl?: string;
		/** CSS `object-position` for the portrait crop. */
		portraitPosition?: string;
		/** A simple numeric count, rendered as a `.count` span. */
		count?: number;
		/** Heading level. `h2` for a top-level shelf group (the default); `h3`
		    when the group is nested under a section-label `h2`, as the topic
		    leaf page's per-author Books groups are — so the outline stays valid. */
		as?: 'h2' | 'h3';
		/** The sticky bordered era-heading variant (Biographies). */
		sticky?: boolean;
		/** Inline content after the name — e.g. an era's year range, or a
		    search group's bespoke "N of M" count. */
		detail?: Snippet;
	} = $props();
</script>

<svelte:element
	this={as}
	class={sticky
		? 'sticky z-10 mb-6 flex items-baseline gap-2 border-b border-border bg-bg pb-2 pt-2 text-h3 text-text'
		: 'mb-4 flex items-center gap-2.5 text-h3 text-muted'}
	style={sticky ? 'top: var(--pinned-offset, 0px)' : undefined}
>
	{#if portraitUrl}
		{@const source = { src: portraitUrl, srcset: portraitSrcset(portraitUrl) }}
		<img
			src={source.src}
			srcset={source.srcset}
			use:hydrateSrc={source}
			sizes="32px"
			alt=""
			loading="lazy"
			width="32"
			height="32"
			class="h-8 w-8 shrink-0 rounded-full border border-border object-cover"
			style="object-position: {portraitPosition}"
		/>
	{/if}
	{#if href}
		<a {href} class="text-text hover:underline">{name}</a>
	{:else}
		{name}
	{/if}
	{@render detail?.()}
	{#if count != null}
		<span class="text-small font-normal count" class:ms-auto={sticky}>{count}</span>
	{/if}
</svelte:element>
