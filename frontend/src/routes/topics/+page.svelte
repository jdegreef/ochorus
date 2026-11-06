<script lang="ts">
	import { isSermonTile, type BookTile, type TopicSummary } from '$lib/library-public';
	import { SITE_URL } from '$lib/config';
	import { itemList, hreflangAll } from '$lib/seo';
	import Seo from '$lib/components/Seo.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import CoverStrip from '$lib/components/CoverStrip.svelte';
	import Emblem from '$lib/components/Emblem.svelte';
	import GroupHeading from '$lib/components/GroupHeading.svelte';
	import { topicMeta } from '$lib/emblemNames';
	import { groupTopics, topicGroupKey } from '$lib/topicGroups';
	import PageHeader from '$lib/components/PageHeader.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';

	let { data } = $props();
	const topics = $derived<TopicSummary[]>(data.topics);
	const loadError = $derived<boolean>(data.loadError);
	const t = i18n.t;

	// Families, not one flat grid of 33 (design review #23). The grouping is
	// data (`topicGroups.ts`), and a shelf placed in no family lands under
	// "More topics" rather than vanishing. No filter field: grouped, the whole
	// hub fits in a few screens, and a filter emptying families under their
	// headings read worse than the map it was searching.
	const groups = $derived(groupTopics(topics));

	// The three book covers a card fans out. Sermon tiles are dropped: a fan is
	// books (CoverStrip takes `BookTile[]`), and a shelf that holds only sermons
	// wears its emblem in the fan's place instead.
	const bookCovers = (tp: TopicSummary): BookTile[] =>
		tp.covers.filter((c): c is BookTile => !isSermonTile(c)).slice(0, 3);

	// One muted line, "17 books · 24 sermons". A zero is dropped rather than
	// printed as "0 books · 5 sermons": a shelf listed on the strength of its
	// sermons is most shelves in most languages (TopicListSerializer.get_covers),
	// and announcing what it does NOT have first made the card contradict itself.
	const countParts = (tp: TopicSummary): string[] =>
		[
			tp.book_count && `${tp.book_count} ${tp.book_count === 1 ? t('common.bookOne') : t('common.bookMany')}`,
			tp.sermon_count &&
				`${tp.sermon_count} ${tp.sermon_count === 1 ? t('common.sermonOne') : t('common.sermonMany')}`
		].filter((p): p is string => !!p);

	// schema.org ItemList of the topical shelves — an ordered roster for crawlers.
	const topicsLd = $derived(
		itemList(
			t('topics.title'),
			topics.map((tp) => ({ name: tp.title, url: localizeHref(`/topics/${tp.slug}`) }))
		)
	);

	// Gated on ADVERTISED_LOCALES, not Paraglide's full `locales`: a locale that
	// is wired in the UI but has an empty catalog must not be advertised to
	// crawlers (see advertised-locales.ts). This page was claiming alternates
	// for draft locales while sitemap.xml, the detail pages and the footer all
	// correctly omitted them — two contradictory claims, with the wrong one on
	// the site's most-crawled pages.
	const hreflang = hreflangAll('/topics');
	const canonical = `${SITE_URL}${localizeHref('/topics')}`;
</script>

<Seo
	title={`${t('topics.title')} — Ochorus`}
	description={t('topics.tagline')}
	{canonical}
	{hreflang}
	ogImage={`${SITE_URL}/og/topics.png`}
	structuredData={topics.length ? [topicsLd] : []}
/>

<div class="page-col px-5 py-10">
	<PageHeader
		title={t('topics.title')}
		tagline={t('topics.tagline')}
		meta={topics.length ? topicCounts : undefined}
	/>
	{#snippet topicCounts()}
		{topics.length}
		{topics.length === 1 ? t('common.topicOne') : t('common.topicMany')}
	{/snippet}

	{#if loadError}
		<EmptyState message={t('common.loadError')} onRetry />
	{:else if topics.length === 0}
		<EmptyState art="language" message={t('topics.none')} />
	{:else}
		{#each groups as group (group.id)}
			<section class="topic-group">
				<GroupHeading name={t(topicGroupKey(group.id))} />
				<div class="topic-grid">
					{#each group.topics as topic (topic.slug)}
						{@const covers = bookCovers(topic)}
						<a class="topic-tile" href={localizeHref(`/topics/${topic.slug}`)}>
							<div class="topic-tile-art">
								{#if covers.length}
									<CoverStrip {covers} size="fan" />
								{:else}
									{@const meta = topicMeta(topic.slug)}
									<span class="emblem-chip topic-tile-emblem" style="--chip-hue: {meta.accent}">
										<Emblem name={meta.emblem} />
									</span>
								{/if}
							</div>
							<h3 class="topic-tile-title">{topic.title}</h3>
							<p class="text-small text-muted">
								{#each countParts(topic) as part, i (i)}{#if i}<span class="sep">{' · '}</span>{/if}{part}{/each}
							</p>
						</a>
					{/each}
				</div>
			</section>
		{/each}
	{/if}
</div>

<style>
	.topic-group + .topic-group {
		margin-top: 3rem;
	}
	/* Two on a phone (a ~165px card still fans three legible covers), three on
	   a tablet, four from a desktop up. */
	.topic-grid {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 2rem 1.25rem;
	}
	@media (min-width: 640px) {
		.topic-grid {
			grid-template-columns: repeat(3, minmax(0, 1fr));
		}
	}
	@media (min-width: 1024px) {
		.topic-grid {
			grid-template-columns: repeat(4, minmax(0, 1fr));
			gap: 2.25rem 1.75rem;
		}
	}
	/* Boxless, like the book card (design #1): the covers carry the colour, so
	   there is no band, no tint and no border — just the fan, the name and one
	   muted line. Its hover is the book card's rise. */
	.topic-tile {
		display: flex;
		flex-direction: column;
		gap: 0.2rem;
		padding: 0.25rem;
		border-radius: var(--radius-card);
		color: inherit;
		transition: transform var(--duration-fast);
	}
	.topic-tile:hover {
		text-decoration: none;
		transform: translateY(-2px);
	}
	@media (prefers-reduced-motion: reduce) {
		.topic-tile,
		.topic-tile:hover {
			transform: none;
		}
	}
	/* The fan's footprint, held by the emblem fallback too, so a sermons-only
	   shelf's card lines up with its neighbours. */
	.topic-tile-art {
		display: grid;
		place-items: center;
		aspect-ratio: 100 / 68;
		margin-bottom: 0.6rem;
	}
	.topic-tile-art > :global(.covers) {
		width: 100%;
	}
	.topic-tile-emblem {
		--chip-size: 6.5rem;
	}
	@media (min-width: 1024px) {
		.topic-tile-title {
			font-size: var(--fs-h3);
		}
	}
	.topic-tile-title {
		font-family: var(--font-display);
		font-size: var(--fs-body);
		font-weight: 600;
		line-height: 1.25;
		color: var(--text);
		transition: color var(--duration-fast);
	}
	.topic-tile:hover .topic-tile-title {
		color: var(--accent);
	}
</style>
