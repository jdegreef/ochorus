<script lang="ts">
	import { scrollEdges } from '$lib/actions/scrollEdges';
	import { citeLine, guideCardLink, type AudienceShelf } from '$lib/library-public';
	import { SITE_URL } from '$lib/config';
	import { breadcrumbLd, collectionPage, hreflangExact } from '$lib/seo';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { contentLang, readingTime } from '$lib/reading';
	import { seriesCompanion } from '$lib/series';
	import {
		heroCovers,
		nextRung,
		RUNG_LABEL,
		hubBooks,
		hubCounts,
		hubIsEmpty,
		hubPaths,
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
	import CoverStrip from '$lib/components/CoverStrip.svelte';
	import Portrait from '$lib/components/Portrait.svelte';
	import PlanShelfCard from '$lib/components/PlanShelfCard.svelte';
	import ArticleCard from '$lib/components/ArticleCard.svelte';
	import Arrow from '$lib/components/Arrow.svelte';
	import ParentsNote from '$lib/components/ParentsNote.svelte';
	import ShareButton from '$lib/components/ShareButton.svelte';
	import QuoteCard from '$lib/components/QuoteCard.svelte';
	import HubContinue from '$lib/components/HubContinue.svelte';
	import HubChallenge from '$lib/components/HubChallenge.svelte';
	import HubSpotlight from '$lib/components/HubSpotlight.svelte';
	import { track } from '$lib/analytics';

	/**
	 * A young-reader hub — /young-readers/ or /teens/ — on the /series index's
	 * anatomy: a browse shelf whose groups are the kinds of thing written for
	 * this audience (series, retold classics, the rest of its topic shelf, plans)
	 * and a note for the adults at the end. Above the shelves it sells rather
	 * than files: a hero band in the audience's hue with a fan of its covers,
	 * "where do you want to start?" cards (each a feeling pointing at one real
	 * place — a wall of covers is where a newcomer gives up), and the lives its
	 * anthologies tell as a strip of faces, each opening its own chapter.
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
	const ready = $derived(!empty && !loadError);
	const counts = $derived(hubCounts(shelf));
	const start = $derived(startPick(shelf));
	const printable = $derived(printableLinks(shelf));
	const paths = $derived(hubPaths(hub, shelf));
	const fan = $derived(heroCovers(shelf));
	const people = $derived(shelf.people ?? []);
	const quotes = $derived(shelf.quotes ?? []);
	const ladders = $derived(shelf.ladders ?? {});
	const challengeSeries = $derived(shelf.series.find((s) => s.slug === hub.challenge.series));
	const leaderGuides = $derived(shelf.leader_guides ?? []);

	// The page's groups, in order, each only when it has something — the jump
	// chips are built from the same list so a chip never points at nothing.
	const sections = $derived(
		[
			{ id: 'people', name: t(hub.peopleHeadingKey), count: people.length },
			{ id: 'series', name: t('nav.series'), count: shelf.series.length },
			{ id: 'retold', name: t('audience.retoldHeading'), count: shelf.editions.length },
			{ id: 'more', name: t('audience.moreHeading'), count: shelf.more.length },
			{ id: 'plans', name: t('nav.plans'), count: shelf.plans.length },
			{ id: 'questions', name: t('audience.questionsHeading'), count: articles.length },
			{ id: 'guides', name: t('audience.guidesHeading'), count: leaderGuides.length }
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
	<!-- The hero band: the audience's hue (the edition ribbons' — cypress for
	     teens, ochre for children) and, from sm, a fan of what is inside. -->
	<section class="hub-hero" data-audience={hub.audience}>
		<div class="min-w-0">
			<PageHeader {title} {tagline} meta={ready ? meta : undefined} />
			{#if ready}
				<!-- How a hub like this travels: one parent to another, one friend to the next. -->
				<div class="-mt-4">
					<ShareButton
						url={canonical}
						{title}
						label={t(hub.shareKey)}
						showLabel
						onshare={() => track(HUB_EVENT, { hub: hub.audience, action: 'share' })}
					/>
				</div>
			{/if}
		</div>
		{#if ready && fan.length}
			<div class="hub-fan">
				<CoverStrip covers={fan} size="fan" priority />
			</div>
		{/if}
	</section>
	{#snippet meta()}
		<span class="whitespace-nowrap"
			>{counts.books} {counts.books === 1 ? t('common.bookOne') : t('common.bookMany')}</span
		>{#if counts.series}{' '}<span class="opacity-50">·</span>{' '}<span class="whitespace-nowrap"
				>{counts.series}
				{counts.series === 1 ? t('common.seriesOne') : t('common.seriesMany')}</span
			>{/if}
	{/snippet}

	{#if loadError}
		<EmptyState message={t('common.loadError')} onRetry />
	{:else if empty}
		<EmptyState message={t('audience.none')} />
	{:else}
		<HubContinue {shelf} exclude={challengeSeries?.slug} />

		{#if paths.length > 1}
			<!-- A few clear first choices above the shelves, by what the reader is
			     after rather than by format — the editor's start pick among them. -->
			<section class="mb-10" aria-labelledby="paths-heading">
				<h2 id="paths-heading" class="section-label mb-3">{t(hub.pathsHeadingKey)}</h2>
				<ul class="paths">
					{#each paths as p (p.href)}
						<li>
							<a
								class="path card-lift"
								href={localizeHref(p.href)}
								onclick={() => track(HUB_EVENT, { hub: hub.audience, action: 'path' })}
							>
								<span class="path-covers"><CoverStrip covers={p.covers} max={3} /></span>
								<span class="min-w-0">
									<span class="block font-display text-h3 font-semibold leading-snug text-text"
										>{t(p.titleKey)}</span
									>
									<span class="mt-1 block text-small text-muted">{t(p.lineKey)} <Arrow /></span>
								</span>
							</a>
						</li>
					{/each}
				</ul>
			</section>
		{:else if start}
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
				{#if !hub.foldParents}
					<a class="tag" href="#parents">{parentsHeading}</a>
				{/if}
			</nav>
		{/if}

		{#if shelf.spotlight}
			<HubSpotlight
				book={shelf.spotlight}
				ladder={ladders[shelf.spotlight.slug]}
				onstart={() => track(HUB_EVENT, { hub: hub.audience, action: 'spotlight' })}
				onclimb={() => track(HUB_EVENT, { hub: hub.audience, action: 'ladder' })}
			/>
		{/if}

		{#if challengeSeries}
			<HubChallenge
				series={challengeSeries}
				challenge={hub.challenge}
				onstart={() => track(HUB_EVENT, { hub: hub.audience, action: 'challenge' })}
			/>
		{/if}

		{#if people.length}
			<section id="people" class="jump-anchor mb-12">
				<GroupHeading name={t(hub.peopleHeadingKey)} />
				<p class="-mt-2 mb-4 max-w-2xl text-small text-muted">{t(hub.peopleNoteKey)}</p>
				<!-- Name and hook are the chapter's own title, in this language. -->
				<ul class="cover-rail flex gap-3 pb-2" use:scrollEdges>
					{#each people as p (`${p.book}/${p.chapter}`)}
						<li class="person">
							<a
								href={localizeHref(`/books/${p.book}/${p.chapter}`)}
								class="person-card card-lift group"
								onclick={() => track(HUB_EVENT, { hub: hub.audience, action: 'person' })}
							>
								<Portrait
									slug={p.slug}
									name={p.name}
									url={p.photo_url}
									px={80}
									class="size-20 rounded-full object-cover"
									initialsClass="text-h3"
									tone="hover"
									decorative
								/>
								<span class="mt-3 block font-display font-semibold leading-snug text-text"
									>{p.name}</span
								>
								<span class="mt-1 block text-small leading-snug text-muted">{p.hook}</span>
								{#if p.words}
									<span class="mt-auto block pt-2 text-eyebrow text-accent"
										>{readingTime(p.words)}</span
									>
								{/if}
							</a>
						</li>
					{/each}
				</ul>
			</section>
		{/if}

		{#if quotes.length}
			<!-- The faces above, in their own words — sourced to the paragraph, with
			     the quote pages' copy and share-as-image actions (English only). -->
			<section class="mb-12" aria-labelledby="quotes-heading">
				<h2 id="quotes-heading" class="section-label mb-4">{t('audience.quotesHeading')}</h2>
				<ul class="grid grid-cols-1 items-stretch gap-5 md:grid-cols-2 lg:grid-cols-3">
					{#each quotes as q (q.slug)}
						<!-- Mixed writers, so the citation leads with whose words they are. -->
						<QuoteCard quote={q} authorName={q.author.name} cite={`${q.author.name}, ${citeLine(q)}`} />
					{/each}
				</ul>
			</section>
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
				<!-- Each retelling's next step up its ladder — the teens edition after
				     the children's, the full original after the teens' — one tap away. -->
				<div class="book-grid cover-rail hub-rail" use:scrollEdges>
					{#each shelf.editions as book (book.slug)}
						{@const next = nextRung(ladders[book.slug], book.slug)}
						<div class="flex flex-col gap-2">
							<BookCard {book} showAuthor perChapter hook={hub.hooks ? book.hook : ''} />
							{#if next}
								<a
									class="ready text-eyebrow"
									href={localizeHref(`/books/${next.slug}`)}
									onclick={() => track(HUB_EVENT, { hub: hub.audience, action: 'ladder' })}
								>
									{t('audience.readyForMore')}
									<span class="font-semibold">{t(RUNG_LABEL[next.rung])}</span>
									<Arrow />
								</a>
							{/if}
						</div>
					{/each}
				</div>
			</section>
		{/if}

		{#if shelf.more.length}
			<section id="more" class="jump-anchor mb-12">
				<GroupHeading name={t('audience.moreHeading')} count={shelf.more.length} />
				<div class="book-grid cover-rail hub-rail" use:scrollEdges>
					{#each shelf.more as book (book.slug)}
						<BookCard
							{book}
							showAuthor
							showSeries
							perChapter
							hook={hub.hooks ? book.hook : ''}
						/>
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

		{#if leaderGuides.length}
			<!-- For the adult running a group: each card opens the book's printable
			     leader's guide, not the book. -->
			<section id="guides" class="jump-anchor mb-12">
				<GroupHeading name={t('audience.guidesHeading')} count={leaderGuides.length} />
				<p class="-mt-2 mb-5 max-w-2xl text-small text-muted">{t('audience.guidesNote')}</p>
				<div class="book-grid">
					{#each leaderGuides as book (book.slug)}
						<BookCard
							{book}
							showAuthor
							showSeries={false}
							link={guideCardLink(book, t)}
						/>
					{/each}
				</div>
			</section>
		{/if}

		<!-- The adult choosing — or reading alongside: free, no account, no ads,
		     how a family or a class might use these, and what prints. Folded shut
		     on the teens hub: the page is the teenager's, the note one tap away. -->
		{#snippet parentsNote()}
			<ParentsNote class="max-w-2xl space-y-2 text-small text-muted">
				<p>{t('audience.parentsFree')}</p>
				<p>{t(hub.parentsTogetherKey)}</p>
				{#if printable.length}
					<p>{t('audience.parentsPrintable')}</p>
					<ul class="flex flex-wrap gap-2 pt-1">
						{#each printable as link (link.href)}
							<!-- A long title wraps inside its pill rather than widening a phone. -->
							<li class="max-w-full">
								<a class="tag max-w-full whitespace-normal" href={localizeHref(link.href)}>{link.label}</a>
							</li>
						{/each}
					</ul>
				{/if}
			</ParentsNote>
		{/snippet}
		{#if hub.foldParents}
			<details id="parents" class="parents-fold jump-anchor">
				<summary class="text-small text-muted">{parentsHeading}</summary>
				<div class="mt-3">{@render parentsNote()}</div>
			</details>
		{:else}
			<section id="parents" class="jump-anchor">
				<GroupHeading name={parentsHeading} />
				{@render parentsNote()}
			</section>
		{/if}
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

	/* The hero band, tinted from the audience's hue — each hue and its -soft
	   twin are defined in every theme, so the band follows lamplight, paper and
	   sepia without a theme rule here. */
	.hub-hero {
		--hub-hue: var(--hue-ochre);
		--hub-soft: var(--hue-ochre-soft);
		display: grid;
		grid-template-columns: minmax(0, 1fr);
		gap: 1.5rem;
		align-items: center;
		margin-bottom: 2.5rem;
		padding: 1.75rem 1.5rem 1.5rem;
		border: 1px solid var(--border);
		border-top: 3px solid var(--hub-hue);
		border-radius: var(--radius-card);
		background: linear-gradient(135deg, var(--hub-soft), var(--surface) 75%);
	}
	.hub-hero[data-audience='teens'] {
		--hub-hue: var(--hue-cypress);
		--hub-soft: var(--hue-cypress-soft);
	}
	/* The fan is decoration: on a phone the words lead and it steps aside. */
	.hub-fan {
		display: none;
	}
	@media (min-width: 640px) {
		.hub-hero {
			grid-template-columns: minmax(0, 1.3fr) minmax(0, 0.7fr);
			gap: 2.5rem;
			padding: 2.25rem 2.5rem;
		}
		.hub-fan {
			display: block;
			max-width: 18rem;
			justify-self: end;
			width: 100%;
		}
	}

	.paths {
		display: grid;
		grid-template-columns: minmax(0, 1fr);
		gap: 0.875rem;
	}
	@media (min-width: 640px) {
		.paths {
			grid-template-columns: repeat(2, minmax(0, 1fr));
		}
	}
	@media (min-width: 1024px) {
		.paths {
			grid-template-columns: repeat(4, minmax(0, 1fr));
		}
	}
	/* Cover beside words until four fit across; then covers on top. */
	.path {
		display: flex;
		align-items: center;
		gap: 0.875rem;
		height: 100%;
		padding: 0.875rem 1rem;
		border: 1px solid var(--border);
		border-radius: var(--radius-card);
		background: var(--surface);
	}
	.path-covers {
		display: block;
		flex: none;
		width: 5.5rem;
	}
	@media (min-width: 1024px) {
		.path {
			flex-direction: column;
			align-items: flex-start;
			padding: 1rem;
		}
		.path-covers {
			width: 7.5rem;
		}
	}

	.person {
		flex: none;
		width: 11rem;
	}
	.person-card {
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		height: 100%;
		padding: 1rem;
		border: 1px solid var(--border);
		border-radius: var(--radius-card);
		background: var(--surface);
	}

	/* On a phone a long shelf swipes sideways — a row per group, as a
	   streaming app would — rather than a wall the reader scrolls past. The
	   scroller itself is the shared .cover-rail (positioned, hidden scrollbar,
	   edge fades, reset on desktop); this only turns the grid into one row.
	   Padding on both sides keeps a card's lift and focus ring unclipped. */
	@media (max-width: 639.98px) {
		.hub-rail {
			grid-template-columns: none;
			grid-auto-flow: column;
			grid-auto-columns: 44%;
			scroll-snap-type: x proximity;
			padding-block: 0.375rem 0.5rem;
		}
		.hub-rail > :global(*) {
			scroll-snap-align: start;
		}
	}
	.ready {
		display: inline-flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.25rem;
		padding-inline: 0.15rem;
		color: var(--accent);
		text-decoration: none;
	}
	.ready:hover {
		text-decoration: underline;
	}

	.parents-fold summary {
		cursor: pointer;
		width: fit-content;
	}
</style>
