<script lang="ts">
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { assetUrl } from '$lib/assetUrl';
	import { hydrateSrc } from '$lib/hydrateSrc';
	import { numeral, volumeLabel, volumeName } from '$lib/series';
	import type { SeriesBook, SeriesMapMarker } from '$lib/library-public';

	/**
	 * A series' world as the journey: its map, a light on each volume's place,
	 * and beside it the volumes in order, each linked. Markers are placed in
	 * percent of the image and labelled with the book's title in this language,
	 * so one map serves every edition. A marker whose volume is not published
	 * here draws nothing. `current` is the volume this reader is in, lit as
	 * "You are here".
	 */
	let {
		image,
		markers,
		books,
		seriesTitle,
		lang,
		current = null
	}: {
		image: string;
		markers: SeriesMapMarker[];
		books: SeriesBook[];
		seriesTitle: string;
		lang: string;
		current?: number | null;
	} = $props();
	const t = i18n.t;

	const source = $derived({ src: assetUrl(image) });
	const stops = $derived(
		markers.flatMap((m) => {
			const book = books.find((b) => b.series_position === m.position);
			if (!book) return [];
			return [{ ...m, book, n: volumeLabel(m.position, lang), name: volumeName(book, seriesTitle) || book.title }];
		})
	);
</script>

<div class="map-wrap">
	<div class="map">
		<img
			src={source.src}
			use:hydrateSrc={source}
			alt={t('series.mapHeading')}
			loading="lazy"
			decoding="async"
		/>
		{#each stops as s (s.position)}
			<a
				href={localizeHref(`/books/${s.book.slug}`)}
				class="marker"
				class:here={s.position === current}
				style="left: {s.x}%; top: {s.y}%"
				aria-label="{s.n} · {s.name}"
			>
				<span class="tip" dir="auto"
					>{s.n} · {s.name}{#if s.position === current} · {t('series.youAreHere')}{/if}</span
				>
			</a>
		{/each}
	</div>
	<ol class="legend">
		{#each stops as s (s.position)}
			<li>
				<span class="key" class:here={s.position === current}
					>{numeral(s.position, lang)}</span
				>
				<a href={localizeHref(`/books/${s.book.slug}`)} dir="auto">{s.name}</a>
				{#if s.position === current}<span class="here-note">{t('series.youAreHere')}</span>{/if}
			</li>
		{/each}
	</ol>
</div>

<style>
	.map-wrap {
		display: grid;
		grid-template-columns: minmax(0, 1.8fr) minmax(0, 1fr);
		gap: 1.5rem;
		align-items: start;
	}
	@media (max-width: 767.98px) {
		.map-wrap {
			grid-template-columns: minmax(0, 1fr);
		}
	}
	.map {
		position: relative;
		border-radius: var(--radius-card);
		overflow: hidden;
		border: 1px solid var(--border);
	}
	.map img {
		display: block;
		width: 100%;
		height: auto;
	}
	/* Markers use physical left/top in their inline style: the map is a picture
	   and is never mirrored, so neither are the places on it. */
	.marker {
		position: absolute;
		width: 2.25rem;
		height: 2.25rem;
		transform: translate(-50%, -50%);
		border-radius: 50%;
		border: 2px solid var(--series-accent, var(--gold));
		background: color-mix(in srgb, var(--series-accent, var(--gold)) 18%, transparent);
		box-shadow: 0 0 0 6px color-mix(in srgb, var(--series-accent, var(--gold)) 14%, transparent);
	}
	.marker.here {
		background: color-mix(in srgb, var(--gold) 55%, transparent);
		box-shadow: 0 0 0 10px rgba(240, 183, 94, 0.35);
	}
	.tip {
		position: absolute;
		bottom: calc(100% + 0.5rem);
		left: 50%; /* rtl-ok: centred over its marker on the unmirrored map */
		transform: translateX(-50%);
		white-space: nowrap;
		padding: 0.25rem 0.5rem;
		border-radius: 0.375rem;
		background: var(--text);
		color: var(--bg);
		font-size: var(--fs-eyebrow);
		opacity: 0;
		pointer-events: none;
		transition: opacity var(--duration-fast, 150ms);
	}
	.marker:hover .tip,
	.marker:focus-visible .tip,
	.marker.here .tip {
		opacity: 1;
	}
	@media (prefers-reduced-motion: no-preference) {
		.marker.here {
			animation: glow 2.4s ease-in-out infinite;
		}
		@keyframes glow {
			50% {
				box-shadow: 0 0 0 16px rgba(240, 183, 94, 0.12);
			}
		}
	}
	.legend {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 0.75rem;
	}
	.legend li {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		flex-wrap: wrap;
	}
	.legend a {
		font-family: var(--font-display);
		font-weight: 600;
		color: var(--text);
	}
	.key {
		display: inline-grid;
		place-items: center;
		width: 1.75rem;
		height: 1.75rem;
		border-radius: 50%;
		border: 2px solid var(--series-accent, var(--gold));
		color: var(--series-accent, var(--gold));
		font-size: var(--fs-eyebrow);
		font-weight: 700;
		flex: none;
	}
	.key.here {
		background: var(--series-accent, var(--gold));
		color: var(--accent-contrast);
	}
	.here-note {
		font-size: var(--fs-eyebrow);
		color: var(--muted);
	}
</style>
