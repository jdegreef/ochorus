<script lang="ts">
	import type { TopicDetail } from '$lib/library';
	import { SITE_URL } from '$lib/config';
	import { absUrl, jsonLd, breadcrumb, hreflangFor } from '$lib/seo';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { scopedSearchHref } from '$lib/searchState';
	import BookCard from '$lib/components/BookCard.svelte';
	import SermonCard from '$lib/components/SermonCard.svelte';
	import Seo from '$lib/components/Seo.svelte';
	import Breadcrumb from '$lib/components/Breadcrumb.svelte';
	import Emblem from '$lib/components/Emblem.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import { topicMeta } from '$lib/emblemNames';

	let { data } = $props();
	const t = i18n.t;
	const topic = $derived<TopicDetail>(data.topic);
	const meta = $derived(topicMeta(topic.slug));

	// Self-referential canonical, and hreflang only for the locales this shelf
	// actually exists in. A topic no longer falls back to its English title — it
	// 404s in a locale with no translation — so advertising every locale here
	// would point search engines at missing pages (see hreflangFor, and the
	// same treatment on books/sermons).
	const path = $derived(`/topics/${topic.slug}/`);
	const canonical = $derived(`${SITE_URL}${localizeHref(path)}`);
	const hreflang = $derived(hreflangFor(path, topic.available_languages));
	// One crumb trail feeds both the visible <Breadcrumb> and the JSON-LD.
	const crumbs = $derived([
		{ name: t('common.home'), href: '/' },
		{ name: t('topics.title'), href: '/topics' },
		{ name: topic.title, href: `/topics/${topic.slug}` }
	]);
	const crumbsLd = $derived(
		jsonLd(breadcrumb(crumbs.map((c) => ({ name: c.name, url: c.href }))))
	);
	const topicLd = $derived(
		jsonLd({
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
					url: `${SITE_URL}${localizeHref(`/books/${b.slug}`)}`
				})),
				...topic.sermons.slice(0, 60).map((s) => ({
					'@type': 'CreativeWork',
					name: s.title,
					author: { '@type': 'Person', name: s.author.name },
					url: `${SITE_URL}${localizeHref(`/sermons/${s.slug}`)}`
				}))
			]
		})
	);
</script>

<Seo
	title="{topic.title} — Ochorus"
	description={topic.description}
	{canonical}
	{hreflang}
	ogImage={absUrl('/og/topics.png')}
	structuredData={[topicLd, crumbsLd]}
/>

<div class="mx-auto max-w-5xl px-5 py-10" style="--topic: {meta.accent}">
	<Breadcrumb items={crumbs} />

	<header class="hero mb-8 mt-4">
		<span class="badge emblem-chip"><Emblem name={meta.emblem} /></span>
		<div class="min-w-0">
			<h1 class="text-h1 mb-2">{topic.title}</h1>
			{#if topic.description}
				<!-- No measure cap: the hero is already bounded by the page column, and
				     capping the text at 36rem inside a 64rem card left the whole header
				     bunched against the left edge with half the card empty. -->
				<p class="text-body text-muted">{topic.description}</p>
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
			<!-- A topic is a shelf, and a shelf you can't search is a list you have
			     to read end to end. -->
			{#if topic.books.length || topic.sermons.length}
				<a
					href={localizeHref(scopedSearchHref('topic', topic.slug))}
					class="mt-3 inline-block text-small font-semibold text-accent hover:underline"
					>{t('search.inTopic')} →</a
				>
			{/if}
		</div>
	</header>

	{#if topic.books.length === 0 && topic.sermons.length === 0}
		<EmptyState message={t('topics.empty')} />
	{/if}

	{#if topic.books.length}
		<section class="mb-10">
			<h2 class="section-label">{t('topics.books')}</h2>
			<div class="book-grid">
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
		border-radius: var(--radius-card);
		border: 1px solid color-mix(in srgb, var(--topic) 22%, var(--color-border));
		background:
			radial-gradient(90% 130% at 0% 0%, color-mix(in srgb, var(--topic) 16%, transparent), transparent 55%),
			color-mix(in srgb, var(--topic) 7%, var(--color-surface));
	}
	/* The hero's emblem chip (recipe in app.css) — only size and hue here. */
	.badge {
		--chip-size: 3.9rem;
		--chip-hue: var(--topic);
	}
	/* A themed Scripture epigraph, set off by an accent rule.

	   No max-width: the 34rem cap stopped the epigraph a third of the way across
	   the card, which — with the description capped too — left the whole hero
	   hugging the left edge. The page column already bounds the measure.
	   padding-inline-start, not padding-left, so the rule stays on the reading
	   edge under RTL (Arabic). */
	.verse {
		margin: 0.9rem 0 0;
		padding-inline-start: 0.9rem;
		border-inline-start: 2px solid color-mix(in srgb, var(--topic) 55%, var(--color-border));
	}
	.verse blockquote {
		margin: 0;
		font-family: var(--font-display, Georgia, serif);
		font-style: italic;
		font-size: var(--fs-body);
		line-height: 1.5;
		color: var(--color-text);
	}
	.verse figcaption {
		margin-top: 0.3rem;
		font-size: var(--fs-small);
		letter-spacing: 0.02em;
		color: color-mix(in srgb, var(--topic) 70%, var(--color-muted));
	}
</style>
