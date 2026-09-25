<script lang="ts">
	import { onMount } from 'svelte';
	import { authorPath } from '$lib/originals';
	import { afterNavigate } from '$app/navigation';
	import type { TopicDetail } from '$lib/library-public';
	import { SITE_URL } from '$lib/config';
	import { readJSON, writeJSON } from '$lib/persisted';
	import { absUrl, jsonLd, breadcrumbLd, hreflangFor, pickQa } from '$lib/seo';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { scopedSearchHref } from '$lib/searchState';
	import BookCard from '$lib/components/BookCard.svelte';
	import BookListRow from '$lib/components/BookListRow.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import SermonCard from '$lib/components/SermonCard.svelte';
	import ArticleCard from '$lib/components/ArticleCard.svelte';
	import PersonCard from '$lib/components/PersonCard.svelte';
	import Seo from '$lib/components/Seo.svelte';
	import Breadcrumb from '$lib/components/Breadcrumb.svelte';
	import Emblem from '$lib/components/Emblem.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import FavoriteButton from '$lib/components/FavoriteButton.svelte';
	import ShareButton from '$lib/components/ShareButton.svelte';
	import QandA from '$lib/components/QandA.svelte';
	import { topicMeta } from '$lib/emblemNames';
	import GroupHeading from '$lib/components/GroupHeading.svelte';
	import { portraitPosition } from '$lib/portraits';
	import { groupBooksByAuthor } from '$lib/topicBookGroups';
	import { topicSectionOrder } from '$lib/topicSections';
	import { matchesBookQuery, sortBooks, type BookSort } from '$lib/bookSort';

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
	// pickQa still centralizes the >=2 floor and the FAQPage JSON-LD. Stored shape
	// is {question, answer}; map to {q, a} for pickQa/faqPage/QandA.
	const qa = $derived(
		pickQa((topic.qa ?? []).map((it) => ({ q: it.question, a: it.answer })), [])
	);

	// Books grouped by author for author-clustered topics (the Puritans), null —
	// a diverse gallery (Women of Faith) that never clusters. See topicBookGroups.
	// When non-null the shelf offers a By-author / All-books toggle; when null
	// there is nothing to group, so the toggle is hidden and it stays flat.
	const bookGroups = $derived(groupBooksByAuthor(topic.books));

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
	afterNavigate(() => (query = ''));
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

	// Content sections led by the type the topic is mostly made of; empties
	// dropped. See topicSectionOrder.
	const sectionOrder = $derived(
		topicSectionOrder({
			books: topic.books.length,
			sermons: topic.sermons.length,
			articles: articles.length
		})
	);

	// Self-referential canonical, and hreflang only for the locales this shelf
	// actually exists in. A topic no longer falls back to its English title — it
	// 404s in a locale with no translation — so advertising every locale here
	// would point search engines at missing pages (see hreflangFor, and the
	// same treatment on books/sermons).
	const path = $derived(`/topics/${topic.slug}/`);
	const canonical = $derived(`${SITE_URL}${localizeHref(path)}`);
	const hreflang = $derived(hreflangFor(path, topic.available_languages));
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

<div class="page-col px-5 py-10" style="--topic: {meta.accent}">
	<Breadcrumb items={crumbs} />

	<!-- Two-column banner: the description and actions run down the main column
	     while the Scripture epigraph sits beside them, so the shelf clears the fold
	     sooner. The verse column wraps under the main one on narrow screens. -->
	<header class="hero mb-8 mt-4">
		<span class="badge emblem-chip"><Emblem name={meta.emblem} /></span>
		<div class="hero-body">
			<div class="hero-main min-w-0">
				<h1 class="text-h1 mb-2">{topic.title}</h1>
				{#if topic.description}
					<!-- No measure cap: the main column is already bounded by its flex
					     basis, so a cap here would strand the text against the left edge. -->
					<p class="text-body text-muted">{topic.description}</p>
				{/if}
				<div class="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2">
					<!-- Follow this shelf: it lands in "My Library" and updates as the
					     topic gains works. -->
					<FavoriteButton kind="topic" slug={topic.slug} showLabel />
					<ShareButton url={canonical} title={topic.title} showLabel />
					<!-- A topic is a shelf, and a shelf you can't search is a list you have
					     to read end to end. -->
					{#if topic.books.length || topic.sermons.length}
						<a
							href={localizeHref(scopedSearchHref('topic', topic.slug))}
							class="inline-block text-small font-semibold text-accent hover:underline"
							>{t('search.inTopic')} →</a
						>
					{/if}
					<span class="text-small text-muted">
						{topic.books.length}
						{topic.books.length === 1 ? t('common.bookOne') : t('common.bookMany')}
						{#if topic.sermons.length}
							· {topic.sermons.length}
							{topic.sermons.length === 1 ? t('common.sermonOne') : t('common.sermonMany')}
						{/if}
						{#if articles.length}
							· {articles.length}
							{articles.length === 1 ? t('common.articleOne') : t('common.articleMany')}
						{/if}
					</span>
				</div>
			</div>
			{#if topic.scripture_text}
				<figure class="verse hero-verse">
					<blockquote>{topic.scripture_text}</blockquote>
					{#if topic.scripture_ref}
						<figcaption>— {topic.scripture_ref}</figcaption>
					{/if}
				</figure>
			{/if}
		</div>
	</header>

	{#if topic.books.length === 0 && topic.sermons.length === 0 && articles.length === 0}
		<EmptyState message={t('topics.empty')} />
	{/if}

	<!-- Filtered the shelf down to nothing: offer to clear the query (mirrors the
	     /books shelf's no-results action). -->
	{#snippet clearFiltersAction()}
		<button class="btn btn-ghost" onclick={clearQuery}>{t('common.clearFilters')}</button>
	{/snippet}

	{#snippet booksSection()}
		<section class="mb-10">
			<h2 class="section-heading">{t('topics.books')}</h2>

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
							<option value="shelf">{t('common.sortShelf')}</option>
							<option value="title">{t('common.sortTitle')}</option>
							<option value="longest">{t('common.sortLongest')}</option>
							<option value="shortest">{t('common.sortShortest')}</option>
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
				<EmptyState message={t('books.noResults')} action={clearFiltersAction} />
			{:else if bookGroups && group === 'author'}
				<!-- Grouped by author. The heading names the author, so the cards below
				     it don't repeat it (list rows drop their author for the same reason). -->
				<div class="flex flex-col gap-8">
					{#each displayGroups ?? [] as g (g.slug)}
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
									{#each g.items as book (book.slug)}
										<BookCard {book} />
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
				     names it. -->
				<div class="book-grid">
					{#each flatBooks as book (book.slug)}
						<BookCard {book} showAuthor />
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

	<!-- Content sections in prominence order: books and sermons lead with the
	     type the topic is mostly made of, articles always come last, empty types
	     dropped. See topicSectionOrder. -->
	{#each sectionOrder as kind (kind)}
		{#if kind === 'books'}{@render booksSection()}
		{:else if kind === 'sermons'}{@render sermonsSection()}
		{:else}{@render articlesSection()}{/if}
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
	/* The banner body beside the emblem: the text column and the Scripture column
	   sit side by side, and the verse wraps under the text when the row can't hold
	   both at their basis (narrow screens). The gap spaces them in either axis. */
	.hero-body {
		display: flex;
		flex-wrap: wrap;
		align-items: flex-start;
		gap: 1rem 1.75rem;
		flex: 1 1 auto;
		min-width: 0;
	}
	.hero-main {
		flex: 1 1 22rem;
	}
	/* The verse as the right-hand column. It keeps the `.verse` accent rule but
	   drops the stacked top margin (the flex gap spaces it now) and is bounded so a
	   long epigraph wraps to more lines rather than crowding the text column. The
	   selector is compounded with `.verse` so the `margin` reset outranks `.verse`'s
	   own `margin` (which is declared later in this block) and the verse top-aligns
	   with the text column. */
	.verse.hero-verse {
		flex: 1 1 15rem;
		max-width: 26rem;
		margin: 0;
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

	/* Related-topics chips: quiet pills in the topic accent, a lateral "see also"
	   row. No physical inline properties — Arabic is a routed locale (rtl.test). */
	.related-topics {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
	}
	.related-topics a {
		padding: 0.3rem 0.8rem;
		border-radius: 999px;
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
