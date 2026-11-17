<script lang="ts">
	import { localizeHref } from '$lib/href';
	import { assetSrcset, assetUrl } from '$lib/assetUrl';
	import { hydrateSrc } from '$lib/hydrateSrc';
	import { i18n } from '$lib/i18n.svelte';
	import { numeral, volumeLabel } from '$lib/series';
	import { plateThumb } from '$lib/plates';
	import type { SeriesBook, SeriesPlate } from '$lib/library-public';

	/**
	 * "From the pages": the full-page plates inside an illustrated series
	 * (The Lamplighters of Gloamhaven), one per chapter, as a row that scrolls
	 * sideways. Each opens its chapter. The picture is the plate's small twin
	 * (`plateThumb`, drawn by backend/scripts/build_plate_thumbs.py); the
	 * caption is the chapter's own title and its book's number.
	 */
	let {
		plates,
		books,
		lang
	}: { plates: SeriesPlate[]; books: SeriesBook[]; lang: string } = $props();

	const position = (slug: string) => books.find((b) => b.slug === slug)?.series_position ?? null;
	const items = $derived(
		plates.map((p) => ({
			...p,
			thumb: plateThumb(p.src),
			where: [volumeLabel(position(p.book), lang), `${i18n.t('continue.chapter')} ${numeral(p.order, lang)}`]
				.filter(Boolean)
				.join(' · ')
		}))
	);
</script>

<ul class="plates">
	{#each items as p (p.src)}
		{@const source = {
			src: assetUrl(p.thumb ?? p.src),
			srcset: p.thumb ? assetSrcset(`${p.thumb} 320w, ${p.src} 900w`) : undefined
		}}
		<li>
			<a href={localizeHref(`/books/${p.book}/${p.order}`)} class="plate">
				<img
					src={source.src}
					srcset={source.srcset}
					sizes="9.5rem"
					use:hydrateSrc={source}
					alt={p.alt}
					width="152"
					height="203"
					loading="lazy"
					decoding="async"
				/>
				<span class="plate-title" dir="auto">{p.chapter}</span>
				<span class="plate-where">{p.where}</span>
			</a>
		</li>
	{/each}
</ul>

<style>
	.plates {
		display: grid;
		grid-auto-flow: column;
		grid-auto-columns: 9.5rem;
		gap: 0.875rem;
		overflow-x: auto;
		overscroll-behavior-x: contain;
		scroll-snap-type: x proximity;
		list-style: none;
		margin: 0;
		padding: 0 0 0.5rem;
	}
	.plates li {
		scroll-snap-align: start;
	}
	.plate {
		display: grid;
		gap: 0.375rem;
		text-decoration: none;
		color: var(--text);
	}
	.plate img {
		display: block;
		width: 100%;
		height: auto;
		aspect-ratio: 3 / 4;
		object-fit: cover;
		border-radius: 0.375rem;
		border: 1px solid var(--border);
		background: var(--surface);
	}
	.plate:hover img {
		border-color: var(--series-accent, var(--accent));
	}
	.plate-title {
		font-size: var(--fs-small);
		font-weight: 600;
		line-height: 1.3;
	}
	.plate-where {
		font-size: var(--fs-eyebrow);
		color: var(--muted);
	}
</style>
