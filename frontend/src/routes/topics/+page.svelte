<script lang="ts">
	import type { TopicSummary } from '$lib/library';
	import { SITE_URL } from '$lib/config';
	import { itemList } from '$lib/seo';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { locales } from '$lib/paraglide/runtime';
	import ShelfCard from '$lib/components/ShelfCard.svelte';
	import { topicMeta } from '$lib/topics';
	import PageHeader from '$lib/components/PageHeader.svelte';

	let { data } = $props();
	const topics = $derived<TopicSummary[]>(data.topics);
	const t = i18n.t;

	// schema.org ItemList of the topical shelves — an ordered roster for crawlers.
	const topicsLd = $derived(
		itemList(
			t('topics.title'),
			topics.map((tp) => ({ name: tp.title, url: localizeHref(`/topics/${tp.slug}`) }))
		)
	);

</script>

<svelte:head>
	<title>{t('topics.title')} — Ochorus</title>
	<meta name="description" content={t('topics.tagline')} />
	<link rel="canonical" href="{SITE_URL}{localizeHref('/topics')}" />
	{#each locales as loc (loc)}
		<link rel="alternate" hreflang={loc} href="{SITE_URL}{localizeHref('/topics', { locale: loc })}" />
	{/each}
	<link rel="alternate" hreflang="x-default" href="{SITE_URL}/topics" />
	<meta property="og:type" content="website" />
	<meta property="og:title" content="{t('topics.title')} — Ochorus" />
	<meta property="og:description" content={t('topics.tagline')} />
	<meta property="og:url" content="{SITE_URL}{localizeHref('/topics')}" />
	<meta property="og:image" content="{SITE_URL}/og/topics.png" />
	<meta name="twitter:card" content="summary_large_image" />
	<!-- eslint-disable-next-line svelte/no-at-html-tags -->
	{#if topics.length}{@html topicsLd}{/if}
</svelte:head>

<div class="page-col px-5 py-10">
	<PageHeader title={t('topics.title')} tagline={t('topics.tagline')} />

	{#if topics.length === 0}
		<p class="text-small text-muted">{t('topics.none')}</p>
	{:else}
		<div class="grid items-stretch gap-5 sm:grid-cols-2">
			{#each topics as topic (topic.slug)}
				{@const meta = topicMeta(topic.slug)}
				<ShelfCard
					href={localizeHref(`/topics/${topic.slug}`)}
					hue={meta.accent}
					icon={meta.icon}
					covers={topic.covers}
					title={topic.title}
				>
					{#snippet aside()}
						{topic.book_count}
						{topic.book_count === 1 ? t('common.bookOne') : t('common.bookMany')}
						{#if topic.sermon_count}
							· {topic.sermon_count}
							{topic.sermon_count === 1 ? t('common.sermonOne') : t('common.sermonMany')}
						{/if}
					{/snippet}
					<p class="shelf-card-desc mt-1.5 text-small text-muted">{topic.description}</p>
				</ShelfCard>
			{/each}
		</div>
	{/if}
</div>

