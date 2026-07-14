<script lang="ts">
	import type { TopicSummary } from '$lib/library';
	import { SITE_URL } from '$lib/config';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/paraglide/runtime';

	let { data } = $props();
	const topics = $derived<TopicSummary[]>(data.topics);
	const t = i18n.t;

	const coverBg = (hex: string) =>
		`linear-gradient(150deg, ${hex || '#3b5bdb'} 0%, #0008 100%)`;
</script>

<svelte:head>
	<title>{t('topics.title')} — Ochorus</title>
	<meta name="description" content={t('topics.tagline')} />
	<link rel="canonical" href="{SITE_URL}/topics" />
	<meta property="og:type" content="website" />
	<meta property="og:title" content="{t('topics.title')} — Ochorus" />
	<meta property="og:url" content="{SITE_URL}/topics" />
</svelte:head>

<div class="mx-auto max-w-5xl px-5 py-10">
	<header class="mb-8">
		<h1 class="text-display mb-2">{t('topics.title')}</h1>
		<p class="max-w-xl text-body text-muted">{t('topics.tagline')}</p>
	</header>

	{#if topics.length === 0}
		<p class="text-small text-muted">{t('topics.none')}</p>
	{:else}
		<div class="grid gap-5 sm:grid-cols-2">
			{#each topics as topic (topic.slug)}
				<a
					href={localizeHref(`/topics/${topic.slug}`)}
					class="group flex flex-col rounded-card border border-border p-5 hover:border-accent hover:bg-surface-2 hover:no-underline"
				>
					<div class="flex items-baseline justify-between gap-3">
						<h2 class="text-h3 text-text group-hover:text-accent">{topic.title}</h2>
						<span class="shrink-0 text-small text-muted">
							{topic.book_count}
							{topic.book_count === 1 ? t('common.bookOne') : t('common.bookMany')}
						</span>
					</div>
					<p class="mt-1.5 flex-1 text-small text-muted">{topic.description}</p>

					{#if topic.covers.length}
						<div class="mt-4 flex gap-2" aria-hidden="true">
							{#each topic.covers as cover (cover.title)}
								<div class="aspect-[3/4] w-12 shrink-0 overflow-hidden rounded-sm shadow-sm">
									{#if cover.cover_url}
										<img
											src={cover.cover_url}
											alt=""
											loading="lazy"
											class="h-full w-full object-cover"
										/>
									{:else}
										<div class="h-full w-full" style="background: {coverBg(cover.cover_color)}"></div>
									{/if}
								</div>
							{/each}
						</div>
					{/if}
				</a>
			{/each}
		</div>
	{/if}
</div>
