<script lang="ts">
	import { coverGradient, coverSrcset } from '$lib/coverArt';
	import type { Snippet } from 'svelte';
	import { isSermonTile, type TopicCover } from '$lib/library';
	import Emblem from '$lib/components/Emblem.svelte';
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
		portrait = '',
		covers = [],
		title,
		aside,
		children
	}: {
		href: string;
		/** The card's accent, any CSS colour. Used only through color-mix(). */
		hue: string;
		/** Illustrated emblem for the badge. Ignored when `portrait` is set. */
		emblem?: EmblemName;
		/** Portrait URL to fill the badge instead of an icon (sermons). */
		portrait?: string;
		
		covers?: TopicCover[];
		title: string;
		/** Right-aligned meta beside the title (counts, day totals). */
		aside?: Snippet;
		/** Body content under the title. */
		children?: Snippet;
	} = $props();
</script>

<a class="shelf-card" style="--shelf-hue: {hue}" {href}>
	<div class="shelf-card-band hue-band">
		<span class="shelf-card-badge emblem-chip">
			{#if portrait}
				<img src={portrait} alt="" loading="lazy" />
			{:else if emblem}
				<Emblem name={emblem} />
			{/if}
		</span>
		{#if covers.length}
			<div class="cover-fan" aria-hidden="true">
				{#each covers.slice(0, 4) as cover (`${cover.kind ?? 'book'}:${cover.slug ?? cover.title}`)}
					{#if isSermonTile(cover)}
						<!-- Round, not a 3:4 tile: the shape is what says "sermon, not a
						     volume" at a glance, which is the whole reason sermons were
						     never given covers. -->
						{@const art = sermonArt(cover.slug)}
						<span class="sermon-tile emblem-chip" style="--chip-hue: {art.hue}">
							<Emblem name={art.emblem} />
						</span>
					{:else}
						<div class="cover">
							{#if cover.cover_url}
								<img
									src={cover.cover_url}
									srcset={coverSrcset(cover.cover_url) || undefined}
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
			<h2 class="shelf-card-title">{title}</h2>
			{#if aside}
				<span class="shrink-0 text-small text-muted">{@render aside()}</span>
			{/if}
		</div>
		{#if children}
			{@render children()}
		{/if}
	</div>
</a>
