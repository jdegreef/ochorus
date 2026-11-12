<script lang="ts">
	/**
	 * The way from one book of the Bible to its neighbours in the canon —
	 * "← Genesis · Leviticus →" — so a reader can walk Genesis to Revelation.
	 *
	 * No mechanism of its own: the neighbours are the book's series block
	 * (`series_block` in the API: the nearest published volumes in this
	 * language, by `series_position`), the same `previous` / `next` the series
	 * line and the reader's "Next in the series" already read. A leaf page's
	 * prev/next pair (page-design): ghost previous, soft-primary next.
	 */
	import type { BookSeries } from '$lib/library-public';
	import { localizeHref } from '$lib/href';
	import { i18n } from '$lib/i18n.svelte';
	import Arrow from '$lib/components/Arrow.svelte';

	let { series, lang }: { series: BookSeries; lang: string } = $props();
	const t = i18n.t;
</script>

{#if series.previous || series.next}
	<nav class="bible-book-nav mt-6 flex flex-wrap items-stretch justify-between gap-3" aria-label={series.title}>
		{#if series.previous}
			<a
				href={localizeHref(`/books/${series.previous.slug}`)}
				class="btn btn-ghost flex-col items-start gap-0.5 text-start"
				rel="prev"
				aria-label="{t('bible.previousBook')}: {series.previous.title}"
			>
				<span class="btn-sub">{t('bible.previousBook')}</span>
				<span dir="auto" {lang}><Arrow back /> {series.previous.title}</span>
			</a>
		{/if}
		{#if series.next}
			<a
				href={localizeHref(`/books/${series.next.slug}`)}
				class="btn btn-primary ms-auto flex-col items-end gap-0.5 text-end"
				rel="next"
				aria-label="{t('bible.nextBook')}: {series.next.title}"
			>
				<span class="btn-sub">{t('bible.nextBook')}</span>
				<span dir="auto" {lang}>{series.next.title} <Arrow /></span>
			</a>
		{/if}
	</nav>
{/if}
