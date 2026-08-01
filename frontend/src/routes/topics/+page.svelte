<script lang="ts">
	import type { TopicSummary } from '$lib/library';
	import { SITE_URL } from '$lib/config';
	import { itemList } from '$lib/seo';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { locales } from '$lib/paraglide/runtime';
	import Icon from '$lib/components/Icon.svelte';
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

	const coverBg = (hex: string) =>
		`linear-gradient(150deg, ${hex || '#3b5bdb'} 0%, #0008 100%)`;
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
		<div class="grid gap-5 sm:grid-cols-2">
			{#each topics as topic (topic.slug)}
				{@const meta = topicMeta(topic.slug)}
				<a class="topic-card" style="--topic: {meta.accent}" href={localizeHref(`/topics/${topic.slug}`)}>
					<div class="shelf">
						<span class="badge"><Icon name={meta.icon} size={20} /></span>
						{#if topic.covers.length}
							<div class="covers" aria-hidden="true">
								{#each topic.covers.slice(0, 4) as cover (cover.title)}
									<div class="cover">
										{#if cover.cover_url}
											<img src={cover.cover_url} alt="" loading="lazy" />
										{:else}
											<div class="cover-fallback" style="background: {coverBg(cover.cover_color)}"></div>
										{/if}
									</div>
								{/each}
							</div>
						{/if}
					</div>
					<div class="body">
						<div class="flex items-baseline justify-between gap-3">
							<h2 class="title">{topic.title}</h2>
							<span class="shrink-0 text-small text-muted">
								{topic.book_count}
								{topic.book_count === 1 ? t('common.bookOne') : t('common.bookMany')}
								{#if topic.sermon_count}
									· {topic.sermon_count}
									{topic.sermon_count === 1 ? t('common.sermonOne') : t('common.sermonMany')}
								{/if}
							</span>
						</div>
						<p class="mt-1.5 text-small text-muted">{topic.description}</p>
					</div>
				</a>
			{/each}
		</div>
	{/if}
</div>

<style>
	.topic-card {
		display: flex;
		flex-direction: column;
		border: 1px solid var(--color-border);
		border-radius: var(--radius-card, 0.9rem);
		overflow: hidden;
		background: var(--color-surface);
		transition: border-color 0.15s, box-shadow 0.15s, transform 0.15s;
	}
	.topic-card:hover {
		border-color: color-mix(in srgb, var(--topic) 55%, var(--color-border));
		box-shadow: 0 6px 20px -12px color-mix(in srgb, var(--topic) 70%, transparent);
		text-decoration: none;
		transform: translateY(-2px);
	}
	/* The "shelf" header carries the topic's colour + a peek of its covers. */
	.shelf {
		position: relative;
		display: flex;
		align-items: flex-end;
		gap: 0.6rem;
		min-height: 5.75rem;
		padding: 1rem 1.1rem 0.9rem;
		background:
			radial-gradient(120% 140% at 0% 0%, color-mix(in srgb, var(--topic) 22%, transparent), transparent 60%),
			color-mix(in srgb, var(--topic) 9%, var(--color-surface-2));
		border-bottom: 1px solid color-mix(in srgb, var(--topic) 22%, var(--color-border));
	}
	.badge {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 2.35rem;
		height: 2.35rem;
		border-radius: 999px;
		color: color-mix(in srgb, var(--topic) 82%, var(--color-text));
		background: color-mix(in srgb, var(--topic) 16%, var(--color-surface));
		box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--topic) 35%, transparent);
		flex-shrink: 0;
	}
	.covers {
		display: flex;
		margin-left: auto;
		padding-left: 0.5rem;
	}
	.cover {
		width: 2.5rem;
		aspect-ratio: 3 / 4;
		border-radius: 0.25rem;
		overflow: hidden;
		box-shadow: 0 2px 6px -2px #0006;
		margin-left: -0.7rem;
		background: var(--color-surface);
		transform: rotate(-3deg);
	}
	.cover:nth-child(2) { transform: rotate(1deg); }
	.cover:nth-child(3) { transform: rotate(4deg); }
	.cover:nth-child(4) { transform: rotate(7deg); }
	.cover img,
	.cover-fallback {
		width: 100%;
		height: 100%;
		object-fit: cover;
	}
	.body {
		padding: 0.9rem 1.1rem 1.15rem;
	}
	.title {
		font-family: var(--font-display, inherit);
		font-size: 1.15rem;
		font-weight: 600;
		color: var(--color-text);
		transition: color 0.15s;
	}
	.topic-card:hover .title {
		color: color-mix(in srgb, var(--topic) 78%, var(--color-text));
	}
	@media (prefers-reduced-motion: reduce) {
		.topic-card,
		.topic-card:hover { transform: none; transition: border-color 0.15s; }
	}
</style>
