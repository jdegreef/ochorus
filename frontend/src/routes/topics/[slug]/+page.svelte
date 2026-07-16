<script lang="ts">
	import type { TopicDetail } from '$lib/library';
	import { SITE_URL } from '$lib/config';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/paraglide/runtime';
	import BookCard from '$lib/components/BookCard.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import { topicMeta } from '$lib/topics';

	let { data } = $props();
	const t = i18n.t;
	const topic = $derived<TopicDetail>(data.topic);
	const meta = $derived(topicMeta(topic.slug));

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

<div class="mx-auto max-w-5xl px-5 py-10" style="--topic: {meta.accent}">
	<a href={localizeHref('/topics')} class="text-small text-muted">← {t('topics.title')}</a>

	<header class="hero mb-8 mt-4">
		<span class="badge"><Icon name={meta.icon} size={26} /></span>
		<div class="min-w-0">
			<h1 class="text-display mb-2">{topic.title}</h1>
			{#if topic.description}
				<p class="max-w-xl text-body text-muted">{topic.description}</p>
			{/if}
			<p class="mt-1 text-small text-muted">
				{topic.books.length}
				{topic.books.length === 1 ? t('common.bookOne') : t('common.bookMany')}
			</p>
		</div>
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

<style>
	.hero {
		display: flex;
		align-items: flex-start;
		gap: 1rem;
		padding: 1.4rem 1.5rem;
		border-radius: var(--radius-card, 0.9rem);
		border: 1px solid color-mix(in srgb, var(--topic) 22%, var(--color-border));
		background:
			radial-gradient(90% 130% at 0% 0%, color-mix(in srgb, var(--topic) 16%, transparent), transparent 55%),
			color-mix(in srgb, var(--topic) 7%, var(--color-surface));
	}
	.badge {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 3.1rem;
		height: 3.1rem;
		flex-shrink: 0;
		border-radius: 999px;
		color: color-mix(in srgb, var(--topic) 82%, var(--color-text));
		background: color-mix(in srgb, var(--topic) 16%, var(--color-surface));
		box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--topic) 35%, transparent);
	}
</style>
