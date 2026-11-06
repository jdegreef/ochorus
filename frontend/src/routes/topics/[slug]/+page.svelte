<script lang="ts">
	import ForPromo from '$lib/components/ForPromo.svelte';
	import { TOPIC_FOR } from '$lib/forPromos';
	import { onMount } from 'svelte';
	import { authorPath } from '$lib/originals';
	import { afterNavigate } from '$app/navigation';
	import type { TopicDetail } from '$lib/library-public';
	import { SITE_URL } from '$lib/config';
	import { readJSON, writeJSON } from '$lib/persisted';
	import { absUrl, jsonLd, breadcrumbLd, hreflangExact, pickQa, toQa } from '$lib/seo';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { tabStrip } from '$lib/actions/tabStrip';
	import { radioKeys } from '$lib/radioKeys';
	import type { Snapshot } from './$types';
	import BookCard from '$lib/components/BookCard.svelte';
	import SeriesCard from '$lib/components/SeriesCard.svelte';
	import { seriesFromBooks } from '$lib/series';
	import BookListRow from '$lib/components/BookListRow.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import SermonCard from '$lib/components/SermonCard.svelte';
	import ArticleCard from '$lib/components/ArticleCard.svelte';
	import PersonCard from '$lib/components/PersonCard.svelte';
	import Seo from '$lib/components/Seo.svelte';
	import Breadcrumb from '$lib/components/Breadcrumb.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import FavoriteButton from '$lib/components/FavoriteButton.svelte';
	import ShareButton from '$lib/components/ShareButton.svelte';
	import QandA from '$lib/components/QandA.svelte';
	import { topicMeta } from '$lib/emblemNames';
	import GroupHeading from '$lib/components/GroupHeading.svelte';
	import { portraitPosition } from '$lib/portraits';
	import { groupBooksByAuthor } from '$lib/topicBookGroups';
	import { topicSectionOrder, topicLeadsWithSeries, type TopicSectionKind } from '$lib/topicSections';
	import { BOOK_SORTS, BOOK_SORT_LABEL, matchesBookQuery, sortBooks, type BookSort } from '$lib/bookSort';

	let { data } = $props();
	const t = i18n.t;
	const topic = $derived<TopicDetail>(data.topic);
	// `articles` is a newer field than books/sermons; default it so a topic
	// served by an API instance that predates it (a rolling-deploy skew) renders
	// without an Articles section rather than throwing.
	const articles = $derived(topic.articles ?? []);
	const ARTICLES_SHOWN = 6;
	let showAllArticles = $state(false);
	// Newer facets than books/sermons; default so an API without them (a
	// rolling-deploy skew) renders those sections away rather than throwing.
	const authors = $derived(topic.authors ?? []);
	const relatedTopics = $derived(topic.related_topics ?? []);
	const meta = $derived(topicMeta(topic.slug));

	// Editorial Q&A about the shelf. Content, per-language via qa_for on the API,
	// so it's not locale-gated here — an untranslated locale simply returns [].
	// Topics have no derived fallback (unlike books), so the second arg is empty;
	// pickQa still centralizes the >=2 floor and the FAQPage JSON-LD.
	const qa = $derived(pickQa(toQa(topic.qa), []));

	// Books grouped by author for author-clustered topics (the Puritans), null —
	// a diverse gallery (Women of Faith) that never clusters. See topicBookGroups.
	// When non-null the shelf offers a By-author / All-books toggle; when null
	// there is nothing to group, so the toggle is hidden and it stays flat.
	const bookGroups = $derived(groupBooksByAuthor(topic.books));
	const topicSeries = $derived(topicLeadsWithSeries(topic.books) ? seriesFromBooks(topic.books) : []);

	// The Books section's controls. Defaults render one flat cover grid in shelf
	// order — the same dense grid the /books shelf shows — so a topic reads
	// consistently with the library; the reader can re-group, re-sort, filter, or
	// switch to a list. All device-local (they describe the reader, not the shelf)
	// and read after mount, so the prerendered HTML always ships the flat default.
	// Same shape and semantics as the /books view preference, under its own key.
	type Group = 'all' | 'author';
	type View = 'grid' | 'list';
	// `-view2`: the key held a bare 'all'|'author' string in the first cut of this
	// shelf; it now holds a {view, sort, group} bundle, so a fresh key avoids
	// reading the old string as an object (a harmless one-time preference reset).
	const PREFS_KEY = 'ochorus:topic-books-view2';
	// The sort/filter/list controls only earn their space once a shelf is big
	// enough that scanning it pays off; below this a topic stays the clean grid it
	// was, with just the group toggle (which is useful at any size).
	const TOOLBAR_MIN_BOOKS = 12;

	let group = $state<Group>('all');
	let sort = $state<BookSort>('shelf');
	let view = $state<View>('grid');
	// The filter text stays in component state, not the URL: a topic subsection is
	// not a standalone shelf to deep-link into (unlike /books, whose filters are a
	// place). SvelteKit reuses this page component across /topics/<slug>
	// navigations, so the filter would otherwise leak from one topic to the next —
	// afterNavigate clears it so every topic opens unfiltered.
	let query = $state('');
	// The open tab, reset with the filter: every topic opens on its first tab.
	// null = "the default", so the prerendered HTML and first paint agree.
	// Back/Forward is the exception: the snapshot brings the tab back, so the
	// scroll position SvelteKit restores still matches the panel it was saved
	// against (Back from the 18th sermon lands on it, not in the books grid).
	let tab = $state<TopicSectionKind | null>(null);
	export const snapshot: Snapshot<TopicSectionKind | null> = {
		capture: () => tab,
		restore: (v) => (tab = v)
	};
	afterNavigate((nav) => {
		query = '';
		if (nav.type !== 'popstate') tab = null;
	});
	onMount(() => {
		const p = readJSON<{ view?: View; sort?: BookSort; group?: Group }>(PREFS_KEY, {});
		if (p.view === 'grid' || p.view === 'list') view = p.view;
		if (p.sort) sort = p.sort;
		if (p.group === 'all' || p.group === 'author') group = p.group;
	});
	const savePrefs = () => writeJSON(PREFS_KEY, { view, sort, group });
	const setGroup = (g: Group) => ((group = g), savePrefs());
	const setView = (v: View) => ((view = v), savePrefs());
	const onSort = (e: Event) => {
		sort = (e.currentTarget as HTMLSelectElement).value as BookSort;
		savePrefs();
	};

	// The toolbar controls are hidden below the size threshold; when hidden their
	// (possibly persisted) values must not silently apply a list/longest the reader
	// can neither see nor undo, so the effective view/sort/query fall back to the
	// defaults there. The group toggle is exempt — it shows at any size.
	const showToolbar = $derived(topic.books.length >= TOOLBAR_MIN_BOOKS);
	const effView = $derived(showToolbar ? view : 'grid');
	const effSort = $derived(showToolbar ? sort : 'shelf');
	// Guarded like view/sort: even though afterNavigate clears query per topic, the
	// guard makes it structurally impossible for a filter to apply where its input
	// isn't shown (no flash between a reused render and the navigate reset).
	const effQuery = $derived(showToolbar ? query.trim().toLowerCase() : '');

	// The flat shelf: filtered by the query, then sorted. matchesBookQuery treats
	// an empty query as "no filter", so this covers the unfiltered case too.
	const flatBooks = $derived(
		sortBooks(
			topic.books.filter((b) => matchesBookQuery(b, effQuery)),
			effSort
		)
	);
	// The grouped shelf: the original author clusters, each filtered + sorted with
	// empties dropped — so the author structure stays stable while membership and
	// order follow the controls.
	const displayGroups = $derived.by(() => {
		if (!bookGroups) return null;
		return bookGroups
			.map((g) => ({ ...g, items: sortBooks(g.items.filter((b) => matchesBookQuery(b, effQuery)), effSort) }))
			.filter((g) => g.items.length > 0);
	});
	// A filter that matched nothing — distinct from a genuinely empty shelf, which
	// topicSectionOrder already drops. The grouped and flat views filter the same
	// partition of topic.books, so flatBooks.length is the match count in both.
	const noResults = $derived(effQuery !== '' && flatBooks.length === 0);
	const clearQuery = () => (query = '');

	// The tabs: Books · Sermons · Articles, empties dropped, books first. See
	// topicSectionOrder.
	const counts = $derived<Record<TopicSectionKind, number>>({
		books: topic.books.length,
		sermons: topic.sermons.length,
		articles: articles.length
	});
	const sectionOrder = $derived(topicSectionOrder(counts));
	const TAB_LABEL: Record<TopicSectionKind, string> = {
		books: 'topics.books',
		sermons: 'topics.sermons',
		articles: 'topics.articles'
	};
	const activeTab = $derived(tab && sectionOrder.includes(tab) ? tab : sectionOrder[0]);
	// The WAI-ARIA tabs pattern: arrows move between tabs, selection follows
	// focus, Left/Right swap under RTL — the same stepping as the radio groups.
	const onTabKey = $derived(
		radioKeys(
			sectionOrder,
			() => activeTab,
			(v) => (tab = v),
			'data-tab'
		)
	);

	// "Start here": the shelf's lead book — the first in the topic's curated
	// order (topic_seed's book list, which the API serves in order). Only on a
	// shelf with more than one book; a lone book is already the whole shelf.
	const startBook = $derived(topic.books.length > 1 ? topic.books[0] : null);

	// Self-referential canonical, and hreflang only for the locales this shelf
	// actually exists in. A topic no longer falls back to its English title — it
	// 404s in a locale with no translation — so advertising every locale here
	// would point search engines at missing pages (see hreflangExact, and the
	// same treatment on books/sermons).
	const path = $derived(`/topics/${topic.slug}/`);
	const canonical = $derived(`${SITE_URL}${localizeHref(path)}`);
	// The API counts only the editions above its works floor, and may return
	// none — hreflangExact then emits no alternates rather than every locale.
	const hreflang = $derived(hreflangExact(path, topic.available_languages));
	// The per-topic share card (npm run og:topics). One value feeds both the
	// og:image meta tag and the CollectionPage JSON-LD image, as on books/sermons.
	const ogImage = $derived(absUrl(`/og/topics/${topic.slug}.png`));
	// The <title> and <meta description> carry the words people search for
	// ("Books on Prayer — Free Christian Classics"), not just the shelf heading.
	// A per-shelf override (topic.seo_title / meta_description, English-owned)
	// wins when present; otherwise fall back to the heading and the shelf blurb,
	// exactly as before. Localized pages have no override yet, so they keep the
	// localized-title default until per-locale overrides ship.
	const titleTag = $derived(topic.seo_title || `${topic.title} — Ochorus`);
	const metaDescription = $derived(topic.meta_description || topic.description);
	// One crumb trail feeds both the visible <Breadcrumb> and the JSON-LD.
	const crumbs = $derived([
		{ name: t('common.home'), href: '/' },
		{ name: t('topics.title'), href: '/topics' },
		{ name: topic.title, href: `/topics/${topic.slug}` }
	]);
	const crumbsLd = $derived(breadcrumbLd(crumbs));
	const topicLd = $derived(
		jsonLd({
			'@context': 'https://schema.org',
			'@type': 'CollectionPage',
			name: topic.title,
			description: topic.description || undefined,
			url: canonical,
			image: ogImage,
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
				})),
				...articles.slice(0, 60).map((a) => ({
					'@type': 'Article',
					name: a.h1,
					url: `${SITE_URL}${localizeHref(`/articles/${a.slug}/`)}`
				}))
			]
		})
	);
</script>

<Seo
	title={titleTag}
	description={metaDescription}
	{canonical}
	{hreflang}
	{ogImage}
	structuredData={[topicLd, crumbsLd, qa.ld].filter(Boolean)}
/>

<!-- A shelf holding only a card or two in this language: served for readers,
     withheld from the index (and from the sitemap) until it fills. -->
<svelte:head>
	{#if topic.indexable === false}<meta name="robots" content="noindex" />{/if}
</svelte:head>

<div class="page-col px-5 py-10" style="--topic: {meta.accent}">
	<Breadcrumb items={crumbs} />

	<!-- A plain header (design review #16): the title with its two quiet icon
	     actions, the shelf's one-line description, and the verse as an epigraph
	     beside them — no tinted box, no badge, no count line (the tabs carry the
	     counts) and no Search button (search lives in the site bar). The verse
	     wraps under the text on narrow screens. -->
	<header class="topic-head mb-6 mt-4">
		<div class="head-main min-w-0">
			<div class="flex items-start gap-2">
				<h1 class="text-h1 min-w-0 flex-1">{topic.title}</h1>
				<!-- Follow this shelf: it lands in "My Library" and updates as the
				     topic gains works. -->
				<div class="head-actions flex shrink-0 items-center">
					<FavoriteButton kind="topic" slug={topic.slug} />
					<ShareButton url={canonical} title={topic.title} />
				</div>
			</div>
			{#if topic.description}
				<p class="mt-2 text-body text-muted">{topic.description}</p>
			{/if}
		</div>
		{#if topic.scripture_text}
			<figure class="verse">
				<blockquote>{topic.scripture_text}</blockquote>
				{#if topic.scripture_ref}
					<figcaption>— {topic.scripture_ref}</figcaption>
				{/if}
			</figure>
		{/if}
	</header>

	{#if topic.books.length === 0 && topic.sermons.length === 0 && articles.length === 0}
		<EmptyState art="language" message={t('topics.empty')} />
	{/if}

	<!-- Filtered the shelf down to nothing: offer to clear the query (mirrors the
	     /books shelf's no-results action). -->
	{#snippet clearFiltersAction()}
		<button class="btn btn-ghost" onclick={clearQuery}>{t('common.clearFilters')}</button>
	{/snippet}

	<!-- The series this topic's books belong to, ahead of the books themselves,
	     when the topic is mostly series volumes (For Young Readers) — otherwise
	     it reads as a wall of near-identical covers. -->
	{#snippet seriesSection()}
		{#if topicSeries.length}
			<section class="mb-10">
				<h2 class="section-heading">{t('nav.series')}</h2>
				<div class="grid items-stretch gap-5 sm:grid-cols-2 lg:grid-cols-3">
					{#each topicSeries as s (s.slug)}
						<SeriesCard series={s} compact />
					{/each}
				</div>
			</section>
		{/if}
	{/snippet}

	{#snippet booksSection()}
		<section class="mb-10">
			<!-- The tab names the books, so the heading is for screen readers only —
			     unless a Book Series row comes first, when it marks where the
			     individual books begin. -->
			<h2 class="section-heading" class:sr-only={!topicSeries.length}>{t('topics.books')}</h2>

			<!-- Shelf controls: the filter / sort / grid-list toolbar appears only on a
			     shelf big enough to need it (showToolbar); the By-author / All-books
			     toggle appears whenever the topic clusters, at any size. The row is
			     omitted entirely when neither applies, so a small flat topic is just
			     its grid. Order mirrors the /books shelf: filter · sort · group · view. -->
			{#if showToolbar || bookGroups}
				<div class="filter-row mb-6">
					{#if showToolbar}
						<input
							bind:value={query}
							type="search"
							class="filter-field grow"
							placeholder={t('books.filterPlaceholder')}
							aria-label={t('books.filterPlaceholder')}
						/>
						<select value={sort} onchange={onSort} class="filter-field" aria-label={t('common.sort')}>
							{#each BOOK_SORTS as v (v)}
								<option value={v}>{t(BOOK_SORT_LABEL[v])}</option>
							{/each}
						</select>
					{/if}
					{#if bookGroups}
						<div class="seg">
							<button
								class:active={group === 'all'}
								onclick={() => setGroup('all')}
								aria-pressed={group === 'all'}>{t('books.groupAll')}</button
							>
							<button
								class:active={group === 'author'}
								onclick={() => setGroup('author')}
								aria-pressed={group === 'author'}>{t('books.groupAuthor')}</button
							>
						</div>
					{/if}
					{#if showToolbar}
						<div class="seg">
							<button
								class:active={effView === 'grid'}
								onclick={() => setView('grid')}
								aria-label={t('books.viewGrid')}
								aria-pressed={effView === 'grid'}><Icon name="grid" /></button
							>
							<button
								class:active={effView === 'list'}
								onclick={() => setView('list')}
								aria-label={t('books.viewList')}
								aria-pressed={effView === 'list'}><Icon name="list" /></button
							>
						</div>
					{/if}
				</div>
			{/if}

			{#if noResults}
				<EmptyState art="search" message={t('books.noResults')} action={clearFiltersAction} />
			{:else if bookGroups && group === 'author'}
				<!-- Grouped by author. The heading names the author, so the cards below
				     it don't repeat it (list rows drop their author for the same reason). -->
				<div class="flex flex-col gap-8">
					{#each displayGroups ?? [] as g, gi (g.slug)}
						<div>
							<GroupHeading
								as="h3"
								name={g.name}
								href={localizeHref(authorPath(g.slug))}
								portraitUrl={g.photo_url}
								portraitPosition={portraitPosition(g.slug)}
								count={g.items.length}
							/>
							{#if effView === 'list'}
								<div class="flex flex-col gap-1">
									{#each g.items as book (book.slug)}
										<BookListRow {book} showAuthor={false} />
									{/each}
								</div>
							{:else}
								<div class="book-grid">
									{#each g.items as book, i (book.slug)}
										<BookCard {book} eager={gi === 0 && i < 6} />
									{/each}
								</div>
							{/if}
						</div>
					{/each}
				</div>
			{:else if effView === 'list'}
				<!-- One flat list — the author rides each row since no heading names it. -->
				<div class="flex flex-col gap-1">
					{#each flatBooks as book (book.slug)}
						<BookListRow {book} />
					{/each}
				</div>
			{:else}
				<!-- One flat cover grid — the default, and the same dense grid the
				     /books shelf shows. The author rides each card since no heading
				     names it. Its first row (six, the grid's widest) loads at once
				     rather than from the lazy queue: on a desktop a cover there is
				     the page's LCP (measured). Only the lead is fetched high, as on
				     the home page's Discover strip — on a phone that row is a screen
				     down, under the topic's own header, and six high fetches there
				     would race the fonts for images nobody can see yet. -->
				<div class="book-grid">
					{#each flatBooks as book, i (book.slug)}
						<BookCard {book} showAuthor priority={i === 0} eager={i < 6} />
					{/each}
				</div>
			{/if}
		</section>
	{/snippet}

	{#snippet sermonsSection()}
		<section class="mb-10">
			<h2 class="section-heading">{t('topics.sermons')}</h2>
			<div class="grid gap-3 sm:grid-cols-2">
				{#each topic.sermons as sermon (sermon.slug)}
					<SermonCard {sermon} showAuthor />
				{/each}
			</div>
		</section>
	{/snippet}

	{#snippet articlesSection()}
		<section class="mb-10">
			<h2 class="section-heading">{t('topics.articles')}</h2>
			<!-- The first few, then "Show N more": a big topic has dozens (Enduring
			     Classics: 61), and they are companions to the shelves above, not the
			     shelf. The rest stay in the HTML (display:none) so the prerendered
			     page still links every article. -->
			<div id="topic-articles" class="grid gap-3 sm:grid-cols-2">
				{#each articles as article, i (article.slug)}
					<div class:hidden={!showAllArticles && i >= ARTICLES_SHOWN}>
						<ArticleCard {article} heading="h3" />
					</div>
				{/each}
			</div>
			{#if articles.length > ARTICLES_SHOWN}
				<button
					type="button"
					class="btn btn-sm btn-ghost mt-3"
					aria-controls="topic-articles"
					aria-expanded={showAllArticles}
					onclick={() => (showAllArticles = !showAllArticles)}
				>
					{showAllArticles
						? t('search.showLess')
						: t('bios.showMore').replace('%n%', String(articles.length - ARTICLES_SHOWN))}
				</button>
			{/if}
		</section>
	{/snippet}

	<!-- The shelf's one pick, ahead of everything: its lead book. -->
	{#snippet startHere()}
		{#if startBook}
			<section class="mb-8 max-w-[36rem]" aria-labelledby="topic-start-here">
				<h2 id="topic-start-here" class="eyebrow mb-1 text-muted">{t('audience.startHeading')}</h2>
				<BookListRow book={startBook} />
			</section>
		{/if}
	{/snippet}

	<!-- Tabs: Books · Sermons · Articles with their counts, books first, empty
	     kinds dropped (topicSectionOrder). A one-kind topic still gets its one
	     tab: it is where the shelf's size is stated. Every panel is in the
	     prerendered HTML — the inactive ones are only `hidden` — so each work
	     stays linked for search engines and the JSON-LD above still lists them
	     all. `tabStrip`: a long language can push the row past a phone's width;
	     it scrolls sideways with the shared edge fade and keeps the active tab
	     in view. -->
	{#if sectionOrder.length}
		<div
			class="topic-tabs tab-strip mb-6"
			role="tablist"
			aria-label={topic.title}
			use:tabStrip={`topic-panel-${activeTab}`}
			tabindex="-1"
			onkeydown={onTabKey}
		>
			{#each sectionOrder as kind (kind)}
				<button
					type="button"
					role="tab"
					id="topic-tab-{kind}"
					data-tab={kind}
					class="subnav-link"
					class:is-active={kind === activeTab}
					aria-selected={kind === activeTab}
					aria-controls="topic-panel-{kind}"
					tabindex={kind === activeTab ? 0 : -1}
					onclick={() => (tab = kind)}
					>{t(TAB_LABEL[kind])} <span class="tab-count">{counts[kind]}</span></button
				>
			{/each}
		</div>
	{/if}
	{#each sectionOrder as kind (kind)}
		<div
			id="topic-panel-{kind}"
			class="topic-panel panel-{kind}"
			role="tabpanel"
			aria-labelledby="topic-tab-{kind}"
			hidden={kind !== activeTab}
		>
			{#if kind === 'books'}{@render startHere()}{@render seriesSection()}{@render booksSection()}
			{:else if kind === 'sermons'}{@render sermonsSection()}
			{:else}{@render articlesSection()}{/if}
		</div>
	{/each}

	<!-- Authors on this shelf: a reader here often wants more of a voice, not
	     only more of the theme. Distinct writers behind the books and sermons. -->
	{#if authors.length}
		<section class="mb-10">
			<h2 class="section-heading">{t('topics.authors')}</h2>
			<div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
				{#each authors as person (person.slug)}
					<PersonCard {person} />
				{/each}
			</div>
		</section>
	{/if}

	<!-- Questions and Answers about the shelf. `qa.items` also feeds the FAQPage
	     JSON-LD in <Seo> via the same pickQa call, so the visible answers and the
	     structured data stay in lockstep. Shared with the book page. -->
	<QandA items={qa.items} title={t('qa.sectionTitle')} headingClass="section-heading" />

	<!-- Related topics: the lateral "see also", so a shelf is a junction rather
	     than a dead end. Sibling shelves that share books, most-shared first. -->
	{#if relatedTopics.length}
		<section>
			<h2 class="section-heading">{t('topics.related')}</h2>
			<nav class="related-topics" aria-label={t('topics.related')}>
				{#each relatedTopics as rel (rel.slug)}
					<a href={localizeHref(`/topics/${rel.slug}`)} data-sveltekit-preload-data="hover"
						>{rel.title}</a
					>
				{/each}
			</nav>
		</section>
	{/if}

	<!-- The ministry cross-link ("Leading others through this?") comes after the
	     shelf, not in its header: it is a next step for a leader, not the
	     reason the reader came. -->
	{#if TOPIC_FOR[topic.slug]}
		<ForPromo place="topic" slugs={[TOPIC_FOR[topic.slug]]} class="mt-10" />
	{/if}
</div>

<style>
	/* The plain header: the title column and the Scripture epigraph side by
	   side, the verse wrapping under the text when the row can't hold both at
	   their basis (phones). No box — the page column is the frame. */
	.topic-head {
		display: flex;
		flex-wrap: wrap;
		align-items: flex-start;
		gap: 1rem 2.5rem;
	}
	.head-main {
		flex: 1 1 24rem;
	}
	/* The icon actions sit on the title's first line. The h1 is taller than a
	   36px icon button, so they are nudged down to its cap height. */
	.head-actions {
		margin-top: 0.35rem;
	}
	/* The verse as a quiet epigraph: muted italic in the display face, set off by
	   a hairline rule in the topic accent, bounded so a long verse wraps rather
	   than crowding the title. padding-inline-start, not padding-left, so the
	   rule stays on the reading edge under RTL (Arabic). */
	.verse {
		flex: 1 1 15rem;
		max-width: 24rem;
		margin: 0;
		padding-inline-start: 0.9rem;
		border-inline-start: 2px solid color-mix(in srgb, var(--topic) 45%, var(--color-border));
	}
	.verse blockquote {
		margin: 0;
		font-family: var(--font-display, Georgia, serif);
		font-style: italic;
		font-size: var(--fs-small);
		line-height: 1.55;
		color: var(--color-muted);
	}
	.verse figcaption {
		margin-top: 0.3rem;
		font-size: var(--fs-small);
		letter-spacing: 0.02em;
		color: var(--color-muted);
	}

	/* The tab bar: the shared `.subnav-link` tab on a hairline, as the book and
	   author pages' sub-navs. A button, so strip the UA button chrome. */
	.topic-tabs {
		display: flex;
		gap: 0.25rem;
		border-bottom: 1px solid var(--color-border);
	}
	.topic-tabs button {
		background: none;
		cursor: pointer;
	}
	.tab-count {
		margin-inline-start: 0.2rem;
		font-variant-numeric: tabular-nums;
	}
	/* Under the tab that already names it, the Sermons / Articles panel's own
	   heading would only repeat the tab; it stays for screen readers and the
	   document outline, visually hidden (Tailwind's `sr-only`, restated: the
	   headings live in snippets shared with another PR's edits, so they are
	   reached from the panel rather than given the class). Each of these panels
	   holds exactly one section. The Books heading takes `sr-only` directly. */
	.panel-sermons > section > .section-heading,
	.panel-articles > section > .section-heading {
		position: absolute;
		width: 1px;
		height: 1px;
		overflow: hidden;
		clip-path: inset(50%);
		white-space: nowrap;
	}

	/* Related-topics chips: quiet pills in the topic accent, a lateral "see also"
	   row. No physical inline properties — Arabic is a routed locale (rtl.test). */
	.related-topics {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
	}
	.related-topics a {
		padding: 0.3rem 0.8rem;
		border-radius: var(--radius-pill);
		border: 1px solid color-mix(in srgb, var(--topic) 28%, var(--color-border));
		background: color-mix(in srgb, var(--topic) 8%, var(--color-surface));
		font-size: var(--fs-small);
		color: var(--color-text);
		text-decoration: none;
	}
	.related-topics a:hover {
		background: color-mix(in srgb, var(--topic) 16%, var(--color-surface));
	}
</style>
