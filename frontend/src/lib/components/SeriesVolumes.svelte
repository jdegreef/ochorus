<script lang="ts">
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { chapterCount, readingTime } from '$lib/reading';
	import { volumeLabel, volumeName, type BookProgress } from '$lib/series';
	import type { SeriesBook } from '$lib/library-public';
	import { assetUrl } from '$lib/assetUrl';
	import { API_BASE_URL } from '$lib/config';
	import BookCover from './BookCover.svelte';
	import Icon from './Icon.svelte';

	/**
	 * An ordered series' volumes as rows that pitch each book: the cover, its
	 * number, its own name (`volumeName`, never the series' name again), the
	 * editor's hook, two lines of blurb, its length, and one button that knows
	 * where this reader is in it. A collection keeps the cover grid — it has no
	 * order to show and no volume names to give.
	 *
	 * `progressOf` is null until mount: progress lives in localStorage, and the
	 * prerendered rows must not bake one visitor's place into every page.
	 */
	let {
		books,
		seriesTitle,
		lang,
		progressOf
	}: {
		books: SeriesBook[];
		seriesTitle: string;
		lang: string;
		progressOf: ((slug: string) => BookProgress) | null;
	} = $props();
	const t = i18n.t;
</script>

<ol class="vols">
	{#each books as book (book.slug)}
		{@const name = volumeName(book, seriesTitle)}
		{@const p = progressOf?.(book.slug) ?? { started: false, finished: false }}
		{@const label = volumeLabel(book.series_position, lang)}
		{@const href = localizeHref(`/books/${book.slug}`)}
		<li class="vol">
			<a {href} class="vol-cover" tabindex="-1" aria-hidden="true">
				<BookCover {book} />
			</a>
			<div class="vol-body">
				{#if label}<p class="eyebrow vol-num">{label}</p>{/if}
				<h3 class="vol-title" dir="auto"><a {href}>{name || book.title}</a></h3>
				{#if book.hook}<p class="vol-hook" dir="auto">{book.hook}</p>{/if}
				{#if book.description}<p class="vol-desc" dir="auto">{book.description}</p>{/if}
				<p class="vol-meta">
					{[chapterCount(book.chapter_count), book.word_count ? readingTime(book.word_count) : '']
						.filter(Boolean)
						.join(' · ')}
				</p>
				{#if book.pdf_url || book.epub_url}
					<!-- The free downloads, marked up as the /for page's book list. -->
					<p class="vol-dl">
						{#if book.pdf_url}
							<a class="btn btn-sm" href={assetUrl(book.pdf_url)} download title={t('book.pdfHint')}
								><Icon name="download" size={14} /> PDF<span class="sr-only" dir="auto"> · {book.title}</span></a
							>
						{/if}
						{#if book.epub_url}
							<a
								class="btn btn-sm"
								href={`${API_BASE_URL}${book.epub_url}`}
								download
								rel="nofollow"
								title={t('book.epubHint')}
								><Icon name="book" size={14} /> EPUB<span class="sr-only" dir="auto"> · {book.title}</span></a
							>
						{/if}
					</p>
				{/if}
			</div>
			<div class="vol-act">
				{#if p.finished}
					<span class="text-small font-medium text-muted">✓ {t('fav.shelfFinished')}</span>
				{:else}
					<a {href} class="btn btn-primary">
						{p.started ? t('plans.continue') : t('book.beginReading')}
					</a>
				{/if}
			</div>
		</li>
	{/each}
</ol>

<style>
	.vols {
		display: grid;
		gap: 0.875rem;
		list-style: none;
		margin: 0;
		padding: 0;
	}
	.vol {
		display: grid;
		grid-template-columns: 6.5rem minmax(0, 1fr) auto;
		gap: 1.25rem;
		align-items: center;
		padding: 1rem 1.25rem 1rem 1rem;
		border: 1px solid var(--border);
		border-radius: var(--radius-card);
		background: var(--surface);
	}
	.vol-cover {
		display: block;
		width: 6.5rem;
	}
	.vol-num {
		color: var(--series-accent, var(--accent));
		margin-bottom: 0.125rem;
	}
	.vol-title {
		font-family: var(--font-display);
		font-size: var(--fs-h3);
		font-weight: 600;
		line-height: 1.2;
		margin: 0 0 0.25rem;
	}
	.vol-title a {
		color: var(--text);
		text-decoration: none;
	}
	.vol-title a:hover {
		text-decoration: underline;
	}
	.vol-hook {
		font-family: var(--font-display);
		font-style: italic;
		color: var(--text);
		margin: 0 0 0.375rem;
		max-width: 60ch;
	}
	.vol-desc {
		color: var(--muted);
		font-size: var(--fs-small);
		max-width: 68ch;
		display: -webkit-box;
		-webkit-line-clamp: 2;
		line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
		margin: 0 0 0.375rem;
	}
	.vol-meta {
		color: var(--muted);
		font-size: var(--fs-small);
		margin: 0;
	}
	.vol-dl {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
		margin: 0.625rem 0 0;
	}
	.vol-act {
		justify-self: end;
	}
	/* A phone: the cover beside the text, the button under both. */
	@media (max-width: 639.98px) {
		.vol {
			grid-template-columns: 5rem minmax(0, 1fr);
			gap: 0.875rem;
			padding: 0.875rem;
		}
		.vol-cover {
			width: 5rem;
		}
		.vol-desc {
			display: none;
		}
		.vol-act {
			grid-column: 1 / -1;
			justify-self: stretch;
			display: grid;
		}
	}
</style>
