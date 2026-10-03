<script lang="ts">
	import { hydrateSrc } from '$lib/hydrateSrc';
	import { coverGradient, coverSrcset } from '$lib/coverArt';
	import type { Snippet } from 'svelte';
	import { isSermonTile, tileFace, type TopicCover } from '$lib/library-public';
	import BookCover from '$lib/components/BookCover.svelte';
	import Emblem from '$lib/components/Emblem.svelte';
	import Monogram from '$lib/components/Monogram.svelte';
	import SermonMonogram from '$lib/components/SermonMonogram.svelte';
	import { sermonArt } from '$lib/sermonArt';
	import type { EmblemName } from '$lib/emblems';

	/**
	 * The shared browse-page card: a colour-washed band carrying an illustrated
	 * emblem (or a portrait) and a fan of covers, over a typographic body.
	 *
	 * This is the Topics card, generalised. It was the best-looking surface in
	 * the app and the only page using it — Plans rendered plain bordered rows
	 * with a ragged cluster of covers floated top-right. Topics and Plans share
	 * it now.
	 *
	 * Sermons does NOT: a sermon shelf carries a 300–400 character brief, which
	 * a banded card cannot hold without becoming mostly text, so the sermons
	 * index uses `<SermonCard variant="row">` instead. (An earlier version of
	 * this note claimed all three shared this card, which sent people looking
	 * for a caller that isn't there.)
	 *
	 * `hue` drives every tint via color-mix (see .shelf-card* in app.css), so a
	 * caller only has to supply a colour and the rest follows.
	 */
	let {
		href,
		hue,
		emblem,
		mark = null,
		portrait = '',
		covers = [],
		title,
		subtitle = '',
		fan = 'sm',
		headingLevel = 2,
		aside,
		children,
		action
	}: {
		href: string;
		/** The card's accent, any CSS colour. Used only through color-mix(). */
		hue: string;
		/** Illustrated emblem for the badge. Ignored when `portrait` or `mark` is set. */
		emblem?: EmblemName;
		/**
		 * A monogram for the badge — label over value: a topic's epigraph
		 * ("JER" over 33) or a plan's length ("DAYS" over 21). Null keeps the emblem (e.g. a topic with no
		 * epigraph translated into this language).
		 */
		mark?: { top: string; value: string } | null;
		/** Portrait URL to fill the badge instead of an icon (sermons). */
		portrait?: string;
		
		covers?: TopicCover[];
		title: string;
		/** A second, smaller line inside the heading — a series' "30 Days with
		 *  God for Girls" — so the heading still carries the whole name. */
		subtitle?: string;
		/** The cover fan's size: `lg` on the series index, where the covers are
		 *  the point of the card — they grow to legible width, centred in the
		 *  band, and the emblem badge steps aside for them. */
		fan?: 'sm' | 'lg';
		/** 2 when the card sits directly under the page's <h1> (Topics, Plans); 3
		 *  when it sits in a section under its own <h2> (the Books page's rail). */
		headingLevel?: 2 | 3;
		/** Right-aligned meta beside the title (counts, day totals). */
		aside?: Snippet;
		/** Body content under the title. */
		children?: Snippet;
		/**
		 * A link of its own at the card's foot — a series' "Start with Brave".
		 * A link can't sit inside the card's link, so with an action the card
		 * becomes a box: the band and body are the card's link, the foot sits
		 * under it, and the box keeps the card's border, lift and hue.
		 */
		action?: Snippet;
	} = $props();
	const bigFan = $derived(fan === 'lg' && covers.length > 0);
</script>

{#snippet content()}
	<div class="shelf-card-band hue-band" class:fan-lg={bigFan}>
		{#if bigFan}
			<!-- The covers carry the card's identity in the large fan. -->
		{:else if mark && !portrait}
			<Monogram class="shelf-card-badge" top={mark.top} value={mark.value} />
		{:else}
			<span class="shelf-card-badge emblem-chip">
				{#if portrait}
					<img src={portrait} use:hydrateSrc={{ src: portrait }} alt="" loading="lazy" />
				{:else if emblem}
					<Emblem name={emblem} />
				{/if}
			</span>
		{/if}
		{#if covers.length}
			<div class="cover-fan" aria-hidden="true">
				{#each covers.slice(0, 4) as cover (`${cover.kind ?? 'book'}:${cover.slug ?? cover.title}`)}
					{#if isSermonTile(cover)}
						<!-- Round, not a 3:4 tile: the shape is what says "sermon, not a
						     volume" at a glance, which is the whole reason sermons were
						     never given covers. It wears its passage monogram, as on
						     every sermon shelf. -->
						<SermonMonogram
							class="sermon-tile"
							hue={sermonArt(cover.slug).hue}
							scriptureRef={cover.scripture_ref}
							title={cover.title}
						/>
					{:else}
						{@const face = tileFace(cover)}
						<div class="cover">
							{#if face}
								<!-- Drawn, not a bare image: a plate ground has no words, so
								     it read as a blank block (mobile review #3). -->
								<BookCover book={face} rounded="" />
							{:else if cover.cover_url}
								{@const source = { src: cover.cover_url, srcset: coverSrcset(cover.cover_url) || undefined }}
								<img
									src={source.src}
									srcset={source.srcset}
									use:hydrateSrc={source}
									alt=""
									loading="lazy"
								/>
							{:else}
								<div
									class="cover-fallback"
									style="background: {coverGradient(cover.cover_color || hue)}"
								></div>
							{/if}
						</div>
					{/if}
				{/each}
			</div>
		{/if}
	</div>
	<div class="shelf-card-body">
		<div class="flex items-baseline justify-between gap-3">
			<svelte:element this={`h${headingLevel}`} class="shelf-card-title"
				>{title}{#if subtitle}<span class="sr-only"> – </span><span
						class="shelf-card-subtitle"
						dir="auto">{subtitle}</span
					>{/if}</svelte:element
			>
			{#if aside}
				<span class="shrink-0 text-small text-muted">{@render aside()}</span>
			{/if}
		</div>
		{#if children}
			{@render children()}
		{/if}
	</div>
{/snippet}

{#if action}
	<div class="shelf-card shelf-card--action card-lift" style="--shelf-hue: {hue}">
		<a class="shelf-card-main" {href}>{@render content()}</a>
		<div class="shelf-card-foot">{@render action()}</div>
	</div>
{:else}
	<a class="shelf-card card-lift" style="--shelf-hue: {hue}" {href}>{@render content()}</a>
{/if}
