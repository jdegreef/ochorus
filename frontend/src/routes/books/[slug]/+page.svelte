<script lang="ts">
	import type { BookDetail } from '$lib/library';
	import { getProgress } from '$lib/progress';
	import { readerPrefs } from '$lib/readerPrefs.svelte';
	import { readingMinutes, readingTime } from '$lib/reading';
	import { SITE_URL } from '$lib/config';
	import { absUrl, jsonLd, breadcrumb, hreflangFor } from '$lib/seo';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/paraglide/runtime';
	import BookCard from '$lib/components/BookCard.svelte';
	import FavoriteButton from '$lib/components/FavoriteButton.svelte';
	import Seo from '$lib/components/Seo.svelte';

	let { data } = $props();
	const t = i18n.t;
	const book = $derived<BookDetail>(data.book);

	let resumeOrder = $state<number | null>(null);
	$effect(() => {
		resumeOrder = getProgress(book.slug);
	});

	const years = $derived(
		book.author.birth_year ? `${book.author.birth_year}–${book.author.death_year ?? ''}` : ''
	);

	const totalWords = $derived(book.chapters.reduce((sum, c) => sum + c.word_count, 0));

	// "Prefer Modern English" (settings): when it's on and this book has a modern
	// edition, the read CTAs open that edition by carrying ?edition=modern. The
	// preference is applied at the link (not in the reader) so the reader's own
	// Modern⇄Original toggle — which represents "original" as *no* param — still
	// works within a session.
	const useModern = $derived(readerPrefs.preferModern && book.has_modern_edition);
	const readHref = (order: number) =>
		localizeHref(`/books/${book.slug}/${order}${useModern ? '?edition=modern' : ''}`);

	// Self-referential canonical + hreflang: this page is prerendered per locale,
	// so each localized copy points at ITSELF (not the English URL, which would
	// deindex the translations) and links its siblings. Books are per-language
	// rows with no English fallback, so hreflang lists only the locales this book
	// actually exists in — see hreflangFor.
	const path = $derived(`/books/${book.slug}/`);
	const canonical = $derived(`${SITE_URL}${localizeHref(path)}`);
	const hreflang = $derived(hreflangFor(path, book.available_languages));
	const description = $derived(
		(book.description || `${book.title} by ${book.author.name} — free to read on Ochorus.`).slice(
			0,
			300
		)
	);
	// og:image must be raster — WhatsApp/Facebook/Twitter refuse SVG preview
	// images. Books without a raster cover fall back to the pre-rasterized PNG
	// of their generated typographic cover (static/covers/<slug>.png; regenerate
	// alongside the SVGs when new coverless books ship).
	const ogImage = $derived(
		book.cover_url && !book.cover_url.endsWith('.svg')
			? absUrl(book.cover_url)
			: absUrl(`/covers/${book.slug}.png`)
	);
	const bookLd = $derived(
		jsonLd({
			'@context': 'https://schema.org',
			'@type': 'Book',
			name: book.title,
			author: { '@type': 'Person', name: book.author.name },
			description: book.description || undefined,
			image: ogImage || undefined,
			inLanguage: book.language,
			url: canonical,
			isAccessibleForFree: true,
			numberOfPages: book.chapter_count
		})
	);
	const crumbsLd = $derived(
		jsonLd(
			breadcrumb([
				{ name: t('common.home'), url: '/' },
				{ name: t('nav.books'), url: '/books' },
				{ name: book.title, url: `/books/${book.slug}` }
			])
		)
	);
</script>

<Seo
	title="{book.title} — {book.author.name} — Ochorus"
	{description}
	{canonical}
	{hreflang}
	ogType="book"
	ogTitle="{book.title} — {book.author.name}"
	{ogImage}
	structuredData={[bookLd, crumbsLd]}
/>

<div class="mx-auto max-w-3xl px-5 py-10">
	<a href={localizeHref('/')} class="text-small text-muted">← {t('common.library')}</a>

	<header class="mt-5 flex flex-col gap-5 sm:flex-row sm:items-start">
		{#if book.cover_url}
			<!-- Intrinsic 3:4 (matches the aspect class) so space is reserved even
			     before app.css applies — the main content image on the page. -->
			<img
				src={book.cover_url}
				alt="{t('a11y.coverOf')} {book.title}"
				width="300"
				height="400"
				class="aspect-[3/4] w-32 shrink-0 rounded-card object-cover shadow-md"
			/>
		{:else}
			<div
				class="flex aspect-[3/4] w-32 shrink-0 items-end rounded-card p-3 shadow-md"
				style="background: linear-gradient(150deg, {book.cover_color || '#3b5bdb'}, #0008)"
			>
				<span style="font-family: var(--font-display)" class="text-base font-semibold text-white">
					{book.title}
				</span>
			</div>
		{/if}

		<div class="flex-1">
			<h1 class="text-h1">{book.title}</h1>
			{#if book.subtitle}<p class="mt-1 text-h3 text-muted">{book.subtitle}</p>{/if}
			<!-- Separator as an expression, not literal text: the span's leading space
			     sits at an {#if} boundary and gets compiler-trimmed, which rendered
			     "Booth· 1829" with the space missing. -->
			<p class="mt-2 text-body">
				<a href={localizeHref(`/authors/${book.author.slug}`)} class="text-accent hover:underline"
					>{book.author.name}</a
				>{#if years}<span class="text-muted">{` · ${years}`}</span>{/if}
			</p>

			{#if book.source_type === 'ai_unreviewed'}
				<p
					class="mt-3 inline-flex items-center gap-1.5 rounded-full border border-gold/40 bg-gold/10 px-3 py-1 text-small text-gold"
				>
					{t('book.aiUnreviewed')}
				</p>
			{:else if book.source_type === 'ai_reviewed'}
				<p
					class="mt-3 inline-flex items-center gap-1.5 rounded-full border border-border bg-surface-2 px-3 py-1 text-small text-muted"
				>
					{t('book.aiReviewed')}
				</p>
			{/if}

			<div class="mt-5 flex flex-wrap items-center gap-3">
				{#if resumeOrder && resumeOrder > 1}
					<a href={readHref(resumeOrder)} class="btn btn-primary">
						{t('book.continueCh')} {resumeOrder}
					</a>
					<a href={readHref(1)} class="btn btn-ghost">{t('book.startOver')}</a>
				{:else}
					<a href={readHref(1)} class="btn btn-primary">{t('book.beginReading')}</a>
				{/if}
				<FavoriteButton kind="book" slug={book.slug} />
				{#if book.pdf_url}
					<a href={book.pdf_url} class="btn btn-ghost" target="_blank" rel="noreferrer">
						{t('book.downloadPdf')}
					</a>
				{/if}
				{#if book.has_modern_edition}
					{@const readOrder = resumeOrder && resumeOrder > 1 ? resumeOrder : 1}
					{#if useModern}
						<!-- Primary CTA already opens modern; offer the original as the alt. -->
						<a href={localizeHref(`/books/${book.slug}/${readOrder}`)} class="btn btn-ghost">
							{t('reader.readOriginal')}
						</a>
					{:else}
						<a
							href={localizeHref(`/books/${book.slug}/${readOrder}?edition=modern`)}
							class="btn btn-ghost"
						>
							{t('book.readModern')}
						</a>
					{/if}
				{/if}
				<span class="text-small text-muted">
					{book.chapter_count}
					{book.chapter_count === 1 ? t('book.chapterOne') : t('book.chaptersMany')} · {readingTime(
						totalWords
					)}{#if book.difficulty}&nbsp;·
						<span title={t('reader.difficulty')}>{t(`reader.difficulty_${book.difficulty}`)}</span>{/if}
				</span>
			</div>
		</div>
	</header>

	{#if book.author.bio}
		<p class="mt-7 max-w-xl text-body text-muted">{book.author.bio}</p>
	{/if}

	{#if book.topics?.length}
		<nav class="mt-6 flex flex-wrap items-center gap-2" aria-label={t('topics.title')}>
			<span class="text-small text-muted">{t('topics.title')}:</span>
			{#each book.topics as topic (topic.slug)}
				<a
					href={localizeHref(`/topics/${topic.slug}`)}
					class="rounded-full border border-border px-3 py-1 text-small text-muted hover:border-accent hover:text-accent hover:no-underline"
				>
					{topic.title}
				</a>
			{/each}
		</nav>
	{/if}

	<section class="mt-9">
		<h2 class="mb-3 text-h3">{t('reader.contents')}</h2>
		<ol class="divide-y divide-border">
			{#each book.chapters as ch (ch.order)}
				<li>
					<a
						href={localizeHref(`/books/${book.slug}/${ch.order}`)}
						class="flex items-baseline gap-3 py-2.5 hover:no-underline"
					>
						<span class="w-6 shrink-0 text-small text-muted">{ch.order}</span>
						<span class="flex-1 text-body text-text">{ch.title}</span>
						<span class="text-[0.8rem] text-muted">{readingMinutes(ch.word_count)} {t('common.min')}</span>
					</a>
				</li>
			{/each}
		</ol>
	</section>

	{#if book.related?.length}
		<section class="mt-12">
			<h2 class="mb-4 text-h3">{t('book.related')}</h2>
			<div class="grid grid-cols-3 gap-x-4 gap-y-6 sm:grid-cols-4 md:grid-cols-6">
				{#each book.related as rel (rel.slug)}
					<BookCard book={rel} showAuthor />
				{/each}
			</div>
		</section>
	{/if}

	{#if book.source_url && book.source_type === 'public_domain'}
		<p class="mt-8 text-[0.8rem] text-muted">
			{t('book.publicDomain')}
			<a href={book.source_url} target="_blank" rel="noreferrer">{t('book.originalEdition')}</a>.
		</p>
	{:else if book.source_url}
		<p class="mt-8 text-[0.8rem] text-muted">
			{t('book.translationOf')}
			<a href={book.source_url} target="_blank" rel="noreferrer">{t('book.originalEdition')}</a>.
		</p>
	{/if}
</div>
