<script lang="ts">
	import type { TopicDetail } from '$lib/library';
	import { SITE_URL } from '$lib/config';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/paraglide/runtime';
	import BookCard from '$lib/components/BookCard.svelte';
	import SermonCard from '$lib/components/SermonCard.svelte';
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
			hasPart: [
				...topic.books.slice(0, 60).map((b) => ({
					'@type': 'Book',
					name: b.title,
					author: { '@type': 'Person', name: b.author.name },
					url: `${SITE_URL}/books/${b.slug}`
				})),
				...topic.sermons.slice(0, 60).map((s) => ({
					'@type': 'CreativeWork',
					name: s.title,
					author: { '@type': 'Person', name: s.author.name },
					url: `${SITE_URL}/sermons/${s.slug}`
				}))
			]
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
			{#if topic.scripture_text}
				<figure class="verse">
					<blockquote>{topic.scripture_text}</blockquote>
					{#if topic.scripture_ref}
						<figcaption>— {topic.scripture_ref}</figcaption>
					{/if}
				</figure>
			{/if}
			<p class="mt-3 text-small text-muted">
				{topic.books.length}
				{topic.books.length === 1 ? t('common.bookOne') : t('common.bookMany')}
				{#if topic.sermons.length}
					· {topic.sermons.length}
					{topic.sermons.length === 1 ? t('common.sermonOne') : t('common.sermonMany')}
				{/if}
			</p>
		</div>
	</header>

	{#if topic.books.length === 0 && topic.sermons.length === 0}
		<p class="text-small text-muted">{t('topics.empty')}</p>
	{/if}

	{#if topic.books.length}
		<section class="mb-10">
			<h2 class="section-label">{t('topics.books')}</h2>
			<div class="grid grid-cols-3 gap-x-4 gap-y-6 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6">
				{#each topic.books as book (book.slug)}
					<BookCard {book} showAuthor />
				{/each}
			</div>
		</section>
	{/if}

	{#if topic.sermons.length}
		<section>
			<h2 class="section-label">{t('topics.sermons')}</h2>
			<div class="grid gap-3 sm:grid-cols-2">
				{#each topic.sermons as sermon (sermon.slug)}
					<SermonCard {sermon} showAuthor />
				{/each}
			</div>
		</section>
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
	.section-label {
		font-size: 0.72rem;
		font-weight: 600;
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: var(--color-muted);
		margin-bottom: 0.9rem;
	}
	/* A themed Scripture epigraph, set off by an accent rule. */
	.verse {
		margin: 0.9rem 0 0;
		padding-left: 0.9rem;
		border-left: 2px solid color-mix(in srgb, var(--topic) 55%, var(--color-border));
		max-width: 34rem;
	}
	.verse blockquote {
		margin: 0;
		font-family: var(--font-display, Georgia, serif);
		font-style: italic;
		font-size: 1.05rem;
		line-height: 1.5;
		color: var(--color-text);
	}
	.verse figcaption {
		margin-top: 0.3rem;
		font-size: 0.8rem;
		letter-spacing: 0.02em;
		color: color-mix(in srgb, var(--topic) 70%, var(--color-muted));
	}
</style>
