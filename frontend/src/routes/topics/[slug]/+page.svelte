<script lang="ts">
	import type { TopicDetail } from '$lib/library';
	import { SITE_URL } from '$lib/config';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/paraglide/runtime';
	import BookCard from '$lib/components/BookCard.svelte';

	let { data } = $props();
	const t = i18n.t;
	const topic = $derived<TopicDetail>(data.topic);

	const canonical = $derived(`${SITE_URL}/topics/${topic.slug}/`);
	const jsonLd = $derived(
		JSON.stringify({
			'@context': 'https://schema.org',
			'@type': 'CollectionPage',
			name: topic.title,
			description: topic.description || undefined,
			url: canonical,
			hasPart: topic.books.slice(0, 60).map((b) => ({
				'@type': 'Book',
				name: b.title,
				author: { '@type': 'Person', name: b.author.name },
				url: `${SITE_URL}/books/${b.slug}`
			}))
		}).replace(/</g, '\\u003c')
	);
</script>

<svelte:head>
	<title>{topic.title} — Ochorus</title>
	<meta name="description" content={topic.description} />
	<link rel="canonical" href={canonical} />
	<meta property="og:type" content="website" />
	<meta property="og:title" content="{topic.title} — Ochorus" />
	<meta property="og:description" content={topic.description} />
	<meta property="og:url" content={canonical} />
	<!-- eslint-disable-next-line svelte/no-at-html-tags -->
	{@html `<script type="application/ld+json">${jsonLd}<\/script>`}
</svelte:head>

<div class="mx-auto max-w-5xl px-5 py-10">
	<a href={localizeHref('/topics')} class="text-small text-muted">← {t('topics.title')}</a>

	<header class="mb-8 mt-4">
		<h1 class="text-display mb-2">{topic.title}</h1>
		{#if topic.description}
			<p class="max-w-xl text-body text-muted">{topic.description}</p>
		{/if}
		<p class="mt-1 text-small text-muted">
			{topic.books.length}
			{topic.books.length === 1 ? t('common.bookOne') : t('common.bookMany')}
		</p>
	</header>

	{#if topic.books.length === 0}
		<p class="text-small text-muted">{t('topics.empty')}</p>
	{:else}
		<div class="grid grid-cols-3 gap-x-4 gap-y-6 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6">
			{#each topic.books as book (book.slug)}
				<BookCard {book} showAuthor />
			{/each}
		</div>
	{/if}
</div>
