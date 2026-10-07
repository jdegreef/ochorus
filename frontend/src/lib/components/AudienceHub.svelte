<script lang="ts">
	import { scrollEdges } from '$lib/actions/scrollEdges';
	import type { AudienceShelf } from '$lib/library-public';
	import { SITE_URL } from '$lib/config';
	import { breadcrumbLd, collectionPage, hreflangExact } from '$lib/seo';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { contentLang } from '$lib/reading';
	import { seriesCompanion } from '$lib/series';
	import {
		hubBooks,
		hubCounts,
		hubIsEmpty,
		printableLinks,
		startPick,
		HUB_EVENT,
		type AudienceHubConfig
	} from '$lib/audienceHub';
	import Seo from '$lib/components/Seo.svelte';
	import PageHeader from '$lib/components/PageHeader.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import GroupHeading from '$lib/components/GroupHeading.svelte';
	import SeriesCard from '$lib/components/SeriesCard.svelte';
	import BookCard from '$lib/components/BookCard.svelte';
	import BookCover from '$lib/components/BookCover.svelte';
	import PlanShelfCard from '$lib/components/PlanShelfCard.svelte';
	import ArticleCard from '$lib/components/ArticleCard.svelte';
	import Arrow from '$lib/components/Arrow.svelte';
	import ParentsNote from '$lib/components/ParentsNote.svelte';
	import ShareButton from '$lib/components/ShareButton.svelte';
	import { track } from '$lib/analytics';

	/**
	 * A young-reader hub — /young-readers/ or /teens/ — on the /series index's
	 * anatomy: a browse shelf whose groups are the kinds of thing written for
	 * this audience (series, retold classics, the rest of its topic shelf, plans)
	 * with one "Start here" pick above them and a note for the adults at the end.
	 * Everything is from `getAudienceShelf`; `hub` only says which audience and
	 * which voice (`$lib/audienceHub`).
	 */
	let {
		hub,
		shelf,
		loadError
	}: { hub: AudienceHubConfig; shelf: AudienceShelf; loadError: boolean } = $props();
	const t = i18n.t;

	const title = $derived(t(hub.labelKey));
	const tagline = $derived(t(hub.taglineKey));
	const description = $derived(t(hub.seoDescriptionKey));
	const path = $derived(`${hub.href}/`);

	const empty = $derived(hubIsEmpty(shelf));
	const articles = $derived(shelf.articles ?? []);
	const counts = $derived(hubCounts(shelf));
	const start = $derived(startPick(shelf));
	const printable = $derived(printableLinks(shelf));

	// The page's groups, in order, each only when it has something — the jump
	// chips are built from the same list so a chip never points at nothing.
	const sections = $derived(
		[
			{ id: 'series', name: t('nav.series'), count: shelf.series.length },
			{ id: 'retold', name: t('audience.retoldHeading'), count: shelf.editions.length },
			{ id: 'more', name: t('audience.moreHeading'), count: shelf.more.length },
			{ id: 'plans', name: t('nav.plans'), count: shelf.plans.length },
			{ id: 'questions', name: t('audience.questionsHeading'), count: articles.length }
		].filter((s) => s.count > 0)
	);
	const parentsHeading = $derived(t(hub.parentsHeadingKey));

	const crumbsLd = $derived(
		breadcrumbLd([
			{ name: t('common.home'), href: '/' },
			{ name: title, href: path }
		])
	);
	// Only the languages where the hub has something of its own (the sitemap
	// lists the same set); a locale without any still bakes the page — the footer
	// links it everywhere — as an unindexed empty shelf claiming no alternates.
	const hreflang = $derived(
		hreflangExact(path, shelf.languages) ?? {
			alternates: [],
			xDefault: `${SITE_URL}${localizeHref(path, { locale: 'en' })}`
		}
	);
	const canonical = $derived(`${SITE_URL}${localizeHref(path)}`);
	// schema.org: a free CollectionPage of the hub's series and books — no
	// audience age, as its topic shelf holds classics for every age — and,
	// below, its place under Home.
	const pageLd = $derived(
		collectionPage({
			name: title,
			description,
			url: canonical,
			items: [
				...shelf.series.map((s) => ({ name: s.title, url: localizeHref(`/series/${s.slug}/`) })),
				...hubBooks(shelf).map((b) => ({ name: b.title, url: localizeHref(`/books/${b.slug}`) }))
			]
		})
	);
</script>

<!-- The card is English, like every share card; one per hub (`npm run og:pages`). -->
<Seo
	title={`${t(hub.seoTitleKey)} — Ochorus`}
	{description}
	{canonical}
	{hreflang}
	ogImage={`${SITE_URL}/og${hub.href}.png`}
	structuredData={empty ? [crumbsLd] : [pageLd, crumbsLd]}
/>

<svelte:head>
	{#if empty}
		<meta name="robots" content="noindex" />
	{/if}
</svelte:head>

<div class="page-col px-5 py-10" style="--pinned-offset: var(--appnav-h, 4rem)">
	<PageHeader {title} {tagline} meta={empty || loadError ? undefined : meta} />
	{#snippet meta()}
		<span class="whitespace-nowrap"
			>{counts.books} {counts.books === 1 ? t('common.bookOne') : t('common.bookMany')}</span
		>{#if counts.series}{' '}<span class="opacity-50">·</span>{' '}<span class="whitespace-nowrap"
				>{counts.series}
				{counts.series === 1 ? t('common.seriesOne') : t('common.seriesMany')}</span
			>{/if}
	{/snippet}

	{#if !empty && !loadError}
		<!-- How a hub like this travels: one parent to another, one friend to the next. -->
		<div class="-mt-4 mb-8">
			<ShareButton
				url={canonical}
				{title}
				label={t(hub.shareKey)}
				showLabel
				onshare={() => track(HUB_EVENT, { hub: hub.audience, action: 'share' })}
			/>
		</div>
	{/if}

	{#if loadError}
		<EmptyState message={t('common.loadError')} onRetry />
	{:else if empty}
		<EmptyState message={t('audience.none')} />
	{:else}
		{#if start}
			<!-- One clear first choice above the shelves: a wall of covers is where
			     a newcomer gives up. The book page's read card, pointing at the book. -->
			<section class="mb-8" aria-labelledby="start-here">
				<h2 id="start-here" class="section-label mb-3">{t('audience.startHeading')}</h2>
				<div class="read-card">
					<a
						href={localizeHref(`/books/${start.slug}`)}
						class="start-cover shrink-0"
						tabindex="-1"
						aria-hidden="true"
					>
						<BookCover book={start} />
					</a>
					<div class="read-card-body">
						<p class="text-small text-muted">
							{t(hub.startKey)}
						</p>
						<p class="read-card-title" lang={contentLang(start.language)} dir="auto">
							{start.title}
						</p>
						<p class="mt-0.5 text-small text-muted">{start.author.name}</p>
					</div>
					<div class="read-card-cta">
						<a
							href={localizeHref(`/books/${start.slug}`)}
							class="btn btn-primary"
							onclick={() => track(HUB_EVENT, { hub: hub.audience, action: 'start' })}
							>{t('book.beginReading')}</a
						>
					</div>
				</div>
			</section>
		{/if}

		{#if sections.length > 1}
			<!-- Anchors, not a filter: every card stays in the prerendered page. -->
			<nav class="chip-scroller mb-8 flex gap-2" use:scrollEdges aria-label={title}>
				{#each sections as s (s.id)}
					<a class="tag" href="#{s.id}">{s.name}<span class="count">{s.count}</span></a>
				{/each}
				<a class="tag" href="#parents">{parentsHeading}</a>
			</nav>
		{/if}

		{#if shelf.series.length}
			<section id="series" class="jump-anchor mb-12">
				<GroupHeading name={t('nav.series')} count={shelf.series.length} />
				<div class="grid items-stretch gap-5 sm:grid-cols-2 lg:grid-cols-3">
					{#each shelf.series as s (s.slug)}
						<SeriesCard
							series={s}
							companion={seriesCompanion(s.slug, shelf.series)}
							headingLevel={3}
						/>
					{/each}
				</div>
			</section>
		{/if}

		{#if shelf.editions.length}
			<section id="retold" class="jump-anchor mb-12">
				<GroupHeading name={t('audience.retoldHeading')} count={shelf.editions.length} />
				<!-- The way up the ladder: each retelling's book page cross-links its
				     teens edition and the full original (`editions`). -->
				<p class="-mt-2 mb-5 max-w-2xl text-small text-muted">
					{t(hub.retoldKey)}
				</p>
				<div class="book-grid">
					{#each shelf.editions as book (book.slug)}
						<BookCard {book} showAuthor />
					{/each}
				</div>
			</section>
		{/if}

		{#if shelf.more.length}
			<section id="more" class="jump-anchor mb-12">
				<GroupHeading name={t('audience.moreHeading')} count={shelf.more.length} />
				<div class="book-grid">
					{#each shelf.more as book (book.slug)}
						<BookCard {book} showAuthor showSeries />
					{/each}
				</div>
				{#if shelf.topic}
					<p class="mt-5 text-small">
						<a
							href={localizeHref(`/topics/${shelf.topic.slug}`)}
							class="text-accent hover:underline"
							>{t('audience.topicLink').replace('%topic%', shelf.topic.title)} <Arrow /></a
						>
					</p>
				{/if}
			</section>
		{/if}

		{#if shelf.plans.length}
			<section id="plans" class="jump-anchor mb-12">
				<GroupHeading name={t('nav.plans')} count={shelf.plans.length} />
				<div class="grid items-stretch gap-5 sm:grid-cols-2 lg:grid-cols-3">
					{#each shelf.plans as plan (plan.slug)}
						<PlanShelfCard {plan} headingLevel={3} />
					{/each}
				</div>
			</section>
		{/if}

		{#if articles.length}
			<!-- Companions to the books, not a shelf of their own: each answers a
			     question a reader is actually asking, then points on to a book. -->
			<section id="questions" class="jump-anchor mb-12">
				<GroupHeading name={t('audience.questionsHeading')} count={articles.length} />
				<p class="-mt-2 mb-5 max-w-2xl text-small text-muted">{t('audience.questionsNote')}</p>
				<div class="grid gap-3 sm:grid-cols-2">
					{#each articles as article (article.slug)}
						<ArticleCard {article} heading="h3" />
					{/each}
				</div>
			</section>
		{/if}

		<!-- The adult choosing — or reading alongside: free, no account, no ads,
		     how a family or a class might use these, and what prints. -->
		<section id="parents" class="jump-anchor">
			<GroupHeading name={parentsHeading} />
			<ParentsNote class="max-w-2xl space-y-2 text-small text-muted">
				<p>{t('audience.parentsFree')}</p>
				<p>{t(hub.parentsTogetherKey)}</p>
				{#if printable.length}
					<p>{t('audience.parentsPrintable')}</p>
					<ul class="flex flex-wrap gap-2 pt-1">
						{#each printable as link (link.href)}
							<li><a class="tag" href={localizeHref(link.href)}>{link.label}</a></li>
						{/each}
					</ul>
				{/if}
			</ParentsNote>
		</section>
	{/if}
</div>

<style>
	/* Jump targets clear the pinned app nav (the /series recipe). */
	.jump-anchor {
		scroll-margin-top: calc(var(--pinned-offset) + 0.5rem);
	}
	.start-cover {
		width: 4.5rem;
	}
</style>
