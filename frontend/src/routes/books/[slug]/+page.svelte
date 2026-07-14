<script lang="ts">
	import type { BookDetail } from '$lib/library';
	import { getProgress } from '$lib/progress';
	import { readingMinutes, readingTime } from '$lib/reading';
	import { SITE_URL } from '$lib/config';
	import { absUrl, jsonLd, breadcrumb } from '$lib/seo';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/paraglide/runtime';

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

	const canonical = $derived(`${SITE_URL}/books/${book.slug}/`);
	const description = $derived(
		(book.description || `${book.title} by ${book.author.name} — free to read on Ochorus.`).slice(
			0,
			300
		)
	);
	const ogImage = $derived(book.cover_url ? absUrl(book.cover_url) : '');
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
				{ name: 'Home', url: '/' },
				{ name: 'Books', url: '/books' },
				{ name: book.title, url: `/books/${book.slug}` }
			])
		)
	);
</script>

<svelte:head>
	<title>{book.title} — {book.author.name} — Ochorus</title>
	<meta name="description" content={description} />
	<link rel="canonical" href={canonical} />
	<meta property="og:type" content="book" />
	<meta property="og:title" content="{book.title} — {book.author.name}" />
	<meta property="og:description" content={description} />
	<meta property="og:url" content={canonical} />
	{#if ogImage}<meta property="og:image" content={ogImage} />{/if}
	<meta name="twitter:card" content={ogImage ? 'summary_large_image' : 'summary'} />
	{@html bookLd}
	{@html crumbsLd}
</svelte:head>

<div class="mx-auto max-w-3xl px-5 py-8">
	<a href={localizeHref('/')} class="text-small text-muted">← {t('common.library')}</a>

	<header class="mt-5 flex flex-col gap-5 sm:flex-row sm:items-start">
		{#if book.cover_url}
			<img
				src={book.cover_url}
				alt="Cover of {book.title}"
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
			<p class="mt-2 text-body">
				<a href={localizeHref(`/authors/${book.author.slug}`)} class="text-accent hover:underline"
					>{book.author.name}</a
				>{#if years}<span class="text-muted"> · {years}</span>{/if}
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
					<a href={localizeHref(`/books/${book.slug}/${resumeOrder}`)} class="btn btn-primary">
						{t('book.continueCh')} {resumeOrder}
					</a>
					<a href={localizeHref(`/books/${book.slug}/1`)} class="btn btn-ghost">{t('book.startOver')}</a>
				{:else}
					<a href={localizeHref(`/books/${book.slug}/1`)} class="btn btn-primary">{t('book.beginReading')}</a>
				{/if}
				{#if book.pdf_url}
					<a href={book.pdf_url} class="btn btn-ghost" target="_blank" rel="noreferrer">
						{t('book.downloadPdf')}
					</a>
				{/if}
				<span class="text-small text-muted">
					{book.chapter_count}
					{book.chapter_count === 1 ? t('book.chapterOne') : t('book.chaptersMany')} · {readingTime(
						totalWords
					)}
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
						<span class="text-[0.8rem] text-muted">{readingMinutes(ch.word_count)} min</span>
					</a>
				</li>
			{/each}
		</ol>
	</section>

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
