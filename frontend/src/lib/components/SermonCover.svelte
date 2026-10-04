<script lang="ts">
	import { sermonArt } from '$lib/sermonArt';
	import { i18n } from '$lib/i18n.svelte';

	/**
	 * A sermon drawn as a book cover: the preacher at the head, "Sermon" over
	 * the title in the middle, the passage at the foot, on a deep ground in the
	 * sermon's own hue. It stands in a resume card's 3:4 cover slot, so a
	 * sermon sits beside the book covers as a peer rather than as an icon tile.
	 *
	 * Nothing is loaded: it is text on a gradient, so it paints with the card.
	 * The hue comes from `sermonArt`, so the sermon keeps the one colour its
	 * plate and share card wear.
	 *
	 * Every length is a container unit, as in `cover-type.css`, so the drawing
	 * holds at any width the slot gives it. The title steps down a size as it
	 * gets longer and clamps after five lines; the card beside it carries the
	 * full title, which is also why the cover is `aria-hidden`.
	 *
	 * hex-ok-file: cream ink and gold on the sermon's own hue — artwork, like a
	 * book cover's ink on its `cover_color`, so it must not follow the theme.
	 */
	let {
		slug,
		title,
		author,
		scriptureRef = ''
	}: { slug: string; title: string; author: string; scriptureRef?: string } = $props();
	const t = i18n.t;

	const hue = $derived(sermonArt(slug).hue);
	const size = $derived(title.length <= 22 ? 'short' : title.length <= 40 ? 'medium' : 'long');
</script>

<div class="sermon-cover rounded-sm" style:--sermon-hue={hue} aria-hidden="true" data-testid="sermon-cover">
	<div class="inner">
		<span class="by">{author}</span>
		<span class="ti {size}"><em>{t('search.typeSermon')}</em>{title}</span>
		{#if scriptureRef}<span class="ref">{scriptureRef}</span>{/if}
	</div>
</div>

<style>
	.sermon-cover {
		container-type: inline-size;
		aspect-ratio: 3 / 4;
		width: 100%;
		overflow: hidden;
		color: #f3ead6;
		background: linear-gradient(
			170deg,
			color-mix(in srgb, var(--sermon-hue) 55%, #101522),
			color-mix(in srgb, var(--sermon-hue) 18%, #0a0d16)
		);
		box-shadow:
			0 1px 2px rgb(0 0 0 / 0.18),
			0 4px 10px rgb(0 0 0 / 0.14);
	}
	.inner {
		box-sizing: border-box;
		height: 100%;
		display: grid;
		grid-template-rows: auto 1fr auto;
		gap: 4cqw;
		padding: 10cqw 8cqw;
		text-align: center;
	}
	.by {
		font-size: 7cqw;
		letter-spacing: 0.18em;
		text-transform: uppercase;
		opacity: 0.75;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.ti {
		align-self: center;
		font-family: var(--font-display);
		font-weight: 600;
		line-height: 1.12;
		overflow-wrap: anywhere;
		hyphens: auto;
		display: -webkit-box;
		-webkit-box-orient: vertical;
		-webkit-line-clamp: 6;
		line-clamp: 6;
		overflow: hidden;
	}
	.ti.short {
		font-size: 14cqw;
	}
	.ti.medium {
		font-size: 11.5cqw;
	}
	.ti.long {
		font-size: 9.5cqw;
	}
	.ti em {
		display: block;
		margin-bottom: 6cqw;
		font-family: var(--font-sans);
		font-style: normal;
		font-weight: 500;
		font-size: 6.5cqw;
		letter-spacing: 0.25em;
		text-transform: uppercase;
		color: #d9b25a;
	}
	.ref {
		padding-top: 5cqw;
		border-top: 1px solid rgb(217 178 90 / 0.45);
		font-family: var(--font-display);
		font-style: italic;
		font-size: 8cqw;
		color: #d9b25a;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
</style>
