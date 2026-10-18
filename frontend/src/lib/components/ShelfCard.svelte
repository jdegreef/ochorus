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
						     volume" at a glance, which is why sermons are
						     given no cover on a shelf. It wears its passage monogram, as on
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

<style>
	/* The shelf card's own parts (band, badge, body, cover fan), moved out of
	   app.css: only this component wears these classes, so the site-wide sheet
	   every page parses and matches against no longer carries them (INP).
	   :global keeps each selector — and its specificity — exactly as it was;
	   the shared .shelf-card / .hue-band recipes stay in app.css. */
	:global {
		/* A shelf card with its own action link (ShelfCard `action`): the box is the
		   card, its band + body are one link, and the action sits in a foot below. */
		.shelf-card-main {
			display: flex;
			flex-direction: column;
			flex: 1;
			color: inherit;
			text-decoration: none;
		}
		.shelf-card-main:hover {
			text-decoration: none;
		}
		/* The link fills the clipped box (overflow: hidden), so its focus ring goes
		   inside it — drawn outside, it was cut off on every edge. */
		.shelf-card-main:focus-visible {
			outline-offset: -2px;
		}
		/* Hovering the foot's own link must not light the card as if the card link
		   were the target: the box rests while the pointer is on the action. */
		.shelf-card--action:has(.shelf-card-foot:hover) {
			border-color: var(--border);
			box-shadow: none;
			transform: none;
		}
		.shelf-card--action:has(.shelf-card-foot:hover) .shelf-card-title {
			color: var(--text);
		}
		.shelf-card--action .shelf-card-body {
			padding-bottom: 0.75rem;
		}
		.shelf-card-foot {
			display: flex;
			flex-direction: column;
			align-items: flex-start;
			gap: 0.6rem;
			padding: 0 1.1rem 1.15rem;
		}
		/* The coloured header band. Pair with .hue-band, which carries the wash. */
		.shelf-card-band {
			--band-hue: var(--shelf-hue);
			position: relative;
			display: flex;
			align-items: flex-end;
			gap: 0.6rem;
			min-height: 5.75rem;
			padding: 1rem 1.1rem 0.9rem;
		}
		/* The shelf card's badge: an emblem chip in the card's hue. */
		.shelf-card-badge {
			--chip-size: 3.5rem;
			--chip-hue: var(--shelf-hue);
		}
		/* A portrait can sit in the chip instead of an icon (the sermons shelf). */
		.shelf-card-badge img {
			width: 100%;
			height: 100%;
			object-fit: cover;
		}
		.shelf-card-body {
			display: flex;
			flex-direction: column;
			flex: 1; /* with .shelf-card{height:100%}, this is what levels the cards */
			padding: 0.9rem 1.1rem 1.15rem;
		}
		.shelf-card-title {
			font-family: var(--font-display);
			font-size: var(--fs-h3);
			font-weight: 600;
			color: var(--text);
			transition: color var(--duration-fast);
		}
		.shelf-card-subtitle {
			display: block;
			margin-top: 0.125rem;
			font-family: var(--font-sans);
			font-size: var(--fs-small);
			font-weight: 400;
			color: var(--muted);
		}
		.shelf-card:hover .shelf-card-title {
			color: color-mix(in srgb, var(--shelf-hue) 78%, var(--text));
		}
		/* The fan of covers in the band. Overlapped (and upright: a book is never
		   drawn on a slant — coverStraight.test.ts) so a shelf reads as books rather
		   than thumbnails. `margin-inline-start:auto` pushes it
		   to the far end; under RTL that is the left, which is correct. */
		/* The band's far end. The band does the pushing, so an occupant only styles
		   itself. */
		.shelf-card-band > :not(.shelf-card-badge) {
			margin-inline-start: auto;
			padding-inline-start: 0.5rem;
			/* Content used to run off the right edge at 375px (it was the one thing
			   wrong with the Topics page on a phone). Clipping it to the band keeps the
			   peek without the overflow. */
			max-width: 62%;
		}

		.cover-fan {
			display: flex;
			overflow: hidden;
		}
		/* The fan's geometry, shared by both tile kinds: the overlap that makes it read
		   as one fanned object, and the lift off the band. */
		.cover-fan > * {
			margin-inline-start: -0.7rem;
			box-shadow: var(--shadow-card);
			flex-shrink: 0;
		}
		.cover-fan .cover {
			width: 2.5rem;
			aspect-ratio: 3 / 4;
			border-radius: 0.25rem;
			overflow: hidden;
			background: var(--surface);
		}
		/* A sermon in the fan: the emblem chip, sized to the tile height. Round rather
		   than 3:4 on purpose — see ShelfCard.

		   The shadow re-states the chip's inset ring alongside the fan's drop shadow.
		   `box-shadow` replaces rather than merges, so setting only the drop shadow
		   here stripped the hairline every other emblem chip in the app wears.

		   And it does NOT take the leading tile's clip. `.cover-fan` hides overflow, so
		   a first tile carrying the -0.7rem pull loses its leading 28% — unnoticeable
		   on a rectangle, which is why covers have always done it, and plainly broken
		   on a circle. A fan that starts with a sermon starts flush instead. */
		.cover-fan .sermon-tile {
			--chip-size: 2.9rem;
			align-self: center;
			box-shadow:
				var(--shadow-card),
				inset 0 0 0 var(--chip-ring, 1px)
					color-mix(in srgb, var(--chip-hue) var(--chip-ring-mix, 33%), transparent);
		}
		.cover-fan .sermon-tile:first-child {
			margin-inline-start: 0;
		}
		/* The large fan (ShelfCard fan="lg", the series index): covers at a width
		   their titles can be read at, centred in a taller band with no badge. The
		   fan pads its block and end edges so the bigger tiles' shadows aren't sliced
		   by its overflow clip. */
		.shelf-card-band.fan-lg {
			justify-content: center;
			min-height: 8.75rem;
			padding-block: 1rem 0.7rem;
		}
		.shelf-card-band.fan-lg > .cover-fan {
			margin-inline-start: 0;
			padding-block: 0.35rem;
			padding-inline: 1.1rem 0.5rem; /* the first tile's pull; the last's shadow */
			max-width: 100%;
		}
		.fan-lg .cover-fan > * {
			margin-inline-start: -1.1rem;
		}
		.fan-lg .cover-fan .cover {
			width: 4.25rem;
		}
		/* The bare-ground fallback only (`> img`): a drawn BookCover inside `.cover`
		   sizes its own images, and this rule would crop its mat. */
		.cover-fan .cover > img,
		.cover-fan .cover-fallback {
			width: 100%;
			height: 100%;
			object-fit: cover;
		}
	}
</style>
