<script lang="ts">
	import Icon from '$lib/components/Icon.svelte';
	import { type AuthorDetail, type AuthorBio, listAuthors, formatLifespan } from '$lib/library-public';
	import { SITE_URL } from '$lib/config';
	import { cssString } from '$lib/cssString';
	import {
		absUrl,
		jsonLd,
		breadcrumbLd,
		faqPage,
		hreflangAll,
		stripHtml,
		truncateMeta,
		itemList,
		topicThings
	} from '$lib/seo';
	import { i18n } from '$lib/i18n.svelte';
	import { readingTime, readingMinutes } from '$lib/reading';
	import { localizeHref } from '$lib/href';
	import Breadcrumb from '$lib/components/Breadcrumb.svelte';
	import { scopedSearchHref } from '$lib/searchState';
	import { initials, portraitPosition } from '$lib/portraits';
	import { listen } from '$lib/listen.svelte';
	import { getLang } from '$lib/lang.svelte';
	import { page } from '$app/stores';
	import { readerPrefs } from '$lib/readerPrefs.svelte';
	import { readerUi } from '$lib/readerUi.svelte';
	import FocusExit from '$lib/components/FocusExit.svelte';
	import { BIO_CHAPTER_ORDER } from '$lib/reading-schema';
	import { bookmarks } from '$lib/bookmarks.svelte';
	import BookCard from '$lib/components/BookCard.svelte';
	import PersonCard from '$lib/components/PersonCard.svelte';
	import FavoriteButton from '$lib/components/FavoriteButton.svelte';
	import Seo from '$lib/components/Seo.svelte';
	import LifeTimeline from '$lib/components/LifeTimeline.svelte';
	import Reader from '$lib/components/Reader.svelte';
	import ReaderControls from '$lib/components/ReaderControls.svelte';
	import SermonCard from '$lib/components/SermonCard.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import { onMount } from 'svelte';

	const t = i18n.t;

	let { data } = $props();
	const author = $derived<AuthorDetail>(data.author);

	// The biography reads like any other long-form work here: <Reader> owns the
	// prose and everything that has to know about it (resume point, highlights
	// and notes, read-aloud, the dictionary and scripture popovers). This page
	// keeps its own shell, because a bio's prose is one band inside a much wider
	// page — the portrait, timeline, book grid and contemporaries must NOT
	// inherit the reading column's width.
	let reader = $state<Reader | undefined>();
	let bioEl = $state<HTMLElement | undefined>();
	/** How far through the biography itself, 0–1 — not through the page. */
	let frac = $state(0);

	onMount(() => readerPrefs.init());

	// --- Bookmarks --------------------------------------------------------------
	// A biography is a single document like a sermon, so `order` is
	// BIO_CHAPTER_ORDER and the paragraph index locates the spot. `headerOffset`
	// is 0 on this page — there is no sticky bar over the prose — and Reader's
	// `topVisibleIndex` honours that, so the answer here matches what the resume
	// point records rather than being a second, differently-calibrated guess.
	let topIndex = $state(0);
	$effect(() => {
		void frac;
		void author.slug;
		topIndex = reader?.topVisibleIndex() ?? 0;
	});
	const currentBookmarked = $derived(bookmarks.has(BIO_CHAPTER_ORDER, topIndex));

	$effect(() => {
		bookmarks.load('bio', author.slug);
	});

	/** Bookmark (or un-bookmark) the paragraph at the top of the viewport. */
	function toggleBookmark() {
		if (!bioEl) return;
		const p = reader?.topVisibleIndex() ?? 0;
		const el = bioEl.children[p] as HTMLElement | undefined;
		const snippet = (el?.innerText ?? '').trim().replace(/\s+/g, ' ').slice(0, 90);
		bookmarks.toggle(BIO_CHAPTER_ORDER, p, snippet, author.name);
		topIndex = p;
	}

	// The bio as plain text, computed once: the word count below and the FAQ's
	// "Who was …" answer both need it, and it is a few-KB string stripped at
	// build time, so a shared derived beats two passes over the same HTML.
	const bioStripped = $derived(stripHtml(author.bio_html || ''));
	// Counted from the rendered bio rather than a word_count field: the API does
	// not expose one for biographies, and this is the only place that needs it.
	const bioWords = $derived(bioStripped.split(/\s+/).filter(Boolean).length);
	const minutesLeft = $derived(Math.max(1, Math.ceil(readingMinutes(bioWords) * (1 - frac))));

	const cite = $derived({
		author: author.name,
		book: t('bios.eyebrow'),
		chapter: '',
		url: $page.url.href
	});

	const years = $derived(
		formatLifespan(author.birth_year, author.death_year, t('common.bornPrefix'))
	);

	// The H1 and the <title> both name what the page actually holds — "<Name>
	// Biography, Books, and Sermons" — rather than the bare name: that is how
	// people search for a writer, and it tells a crawler what the page is. They
	// share one derived string so the two can never drift apart.
	//
	// Each combination is its own message rather than assembled from fragments,
	// because these languages put the name in different places ("Biografía de
	// X", "X की जीवनी") and join lists their own way — concatenation cannot
	// express that. Keys are spelled out rather than built from the parts: a key
	// that does not exist renders as its own name (see i18n.svelte.ts), and
	// nothing in CI catches that, so they are kept greppable.
	//
	// The bio counts only when THIS locale has one — an untranslated bio is
	// absent, and the heading must not promise a life story the page lacks.
	const headingKey = $derived.by(() => {
		const bio = !!(author.bio_html || author.bio);
		const books = author.books.length > 0;
		const sermons = author.sermons.length > 0;
		if (bio && books && sermons) return 'author.headingBioBooksSermons';
		if (bio && books) return 'author.headingBioBooks';
		if (bio && sermons) return 'author.headingBioSermons';
		if (bio) return 'author.headingBio';
		if (books && sermons) return 'author.headingBooksSermons';
		if (books) return 'author.headingBooks';
		if (sermons) return 'author.headingSermons';
		return '';
	});
	const heading = $derived(
		headingKey ? t(headingKey).replace('%name%', author.name) : author.name
	);

	// A one-line "what's here" summary under the name: era + work counts.
	const summaryBits = $derived(
		[
			years,
			author.books.length
				? `${author.books.length} ${author.books.length === 1 ? t('common.bookOne') : t('common.bookMany')}`
				: '',
			author.sermons.length
				? `${author.sermons.length} ${author.sermons.length === 1 ? t('common.sermonOne') : t('common.sermonMany')}`
				: ''
		].filter(Boolean)
	);

	// "More lives to explore": nearest contemporaries by birth year (loaded after
	// mount; the page is prerendered). Falls back to any other authors when this
	// one has no dated birth year.
	let contemporaries = $state<AuthorBio[]>([]);
	onMount(async () => {
		try {
			const all = await listAuthors(getLang());
			const by = author.birth_year;
			const dist = (a: AuthorBio) =>
				by == null || a.birth_year == null ? Infinity : Math.abs(a.birth_year - by);
			contemporaries = all
				.filter((a) => a.slug !== author.slug && (a.book_count > 0 || !!a.bio))
				.sort((a, b) => dist(a) - dist(b) || a.name.localeCompare(b.name))
				.slice(0, 6);
		} catch {
			contemporaries = [];
		}
	});
	// Self-referential canonical + hreflang: this page is prerendered per locale,
	// so each localized copy points at ITSELF (not the English URL) and links its
	// siblings, instead of every locale canonicalizing to /authors/<slug> (which
	// deindexes the translations). Mirrors the /biographies list page.
	const path = $derived(`/authors/${author.slug}/`);
	const canonical = $derived(`${SITE_URL}${localizeHref(path)}`);
	// An author page exists in every locale — the person, their dates and their
	// works are language-independent — so all locales are real hreflang
	// alternates, unlike books/sermons which list only the locales they exist in.
	// (The bio itself no longer falls back to English: an untranslated bio is
	// absent, and the page renders the works without it.)
	const hreflang = $derived(hreflangAll(path));
	// Localized, because the bio may legitimately be missing in this language and
	// a hardcoded English sentence would then become the page's meta description.
	// A bare `.slice(0, 300)` cut the bio mid-word with no ellipsis (a SERP saw
	// "…fourteen great-gr"); truncateMeta ends on a sentence or whole-word boundary
	// within the ~160-char budget scrapers actually display. The book page already
	// routes its description through the same helper.
	const description = $derived(
		truncateMeta(author.bio || t('author.metaFallback').replace('%name%', author.name))
	);
	const ogImage = $derived(
		author.photo_url
			? absUrl(author.photo_url)
			: author.books[0]?.cover_url
				? absUrl(author.books[0].cover_url)
				: ''
	);

	const personLd = $derived(
		jsonLd({
			'@context': 'https://schema.org',
			'@type': 'Person',
			name: author.name,
			description: author.bio || undefined,
			image: ogImage || undefined,
			birthDate: author.birth_year ? String(author.birth_year) : undefined,
			deathDate: author.death_year ? String(author.death_year) : undefined,
			url: canonical,
			// The strongest entity signal the page can carry: it names WHICH
			// person this is, in the vocabularies search and answer engines
			// reconcile against, instead of leaving them to infer it from the
			// prose. Omitted rather than emitted empty when we have none — an
			// empty sameAs asserts nothing and is noise in the markup.
			sameAs: author.same_as?.length ? author.same_as : undefined,
			// The subjects this writer is known for, drawn from the topical shelves
			// their works actually belong to — a machine-readable version of the
			// theme chips the page already shows. Resolvable Things (the shared
			// topicThings shape, same as a Book's `about`) so the person is joined to
			// the topic entities, not just tagged with strings.
			knowsAbout: topicThings(author.topics ?? [])
		})
	);
	// The author→works edges. The book page declares each book's `author`, but the
	// author page never stated the inverse, so the person and their five books were
	// only joined visually. An ItemList of the works — the same structure the
	// browse/shelf pages emit — makes the relationship explicit and orders it the
	// way the page displays it. Sermons are separate CreativeWorks and stay out of
	// a list named for books.
	const worksLd = $derived(
		author.books.length
			? itemList(
					`${t('author.booksBy')} ${author.name}`,
					author.books.map((b) => ({ name: b.title, url: `/books/${b.slug}` }))
				)
			: null
	);
	// One trail feeds both the visible <Breadcrumb> and the JSON-LD, so the
	// on-page path and the structured BreadcrumbList can't drift apart.
	const crumbs = $derived([
		{ name: t('common.home'), href: '/' },
		{ name: t('bios.eyebrow'), href: '/biographies' },
		{ name: author.name, href: `/authors/${author.slug}` }
	]);
	const crumbsLd = $derived(breadcrumbLd(crumbs));
	// Prayer-callout labels are rendered by CSS ::before content; pass the
	// localized strings in as custom properties so they follow the locale.
	// Quoted through cssString: an apostrophe in any translation would close the
	// CSS string early and take the rest of the declaration with it, silently
	// and only in that locale.
	const bioLabels = $derived(
		`--label-in-prayer: ${cssString(t('bios.inPrayer'))}; ` +
			`--label-answered: ${cssString(t('bios.answerToPrayer'))}`
	);

	// Where to start + how much there is to read: the first book (the API's
	// featured order) and the total reading time across every work.
	const startWork = $derived(author.books[0] ?? null);
	const totalWords = $derived(
		author.books.reduce((n, b) => n + (b.word_count ?? 0), 0) +
			author.sermons.reduce((n, s) => n + (s.word_count ?? 0), 0)
	);

	// A featured pull-quote for the header: the first <blockquote> in the bio,
	// tag-stripped (drop the <cite> attribution). Regex, not the DOM, so it works
	// during prerender too. Absent / too-short quotes just don't show.
	const featuredQuote = $derived.by(() => {
		const m = (author.bio_html || '').match(/<blockquote[^>]*>([\s\S]*?)<\/blockquote>/i);
		if (!m) return '';
		const text = stripHtml(m[1].replace(/<cite[\s\S]*?<\/cite>/i, ''))
			.replace(/\s+/g, ' ')
			.trim();
		if (text.length < 20) return '';
		return text.length > 220 ? text.slice(0, 217).trimEnd() + '…' : text;
	});

	// A short FAQ derived from what the page already knows — the life dates, the
	// works, the topical shelves, the opening of the bio. It answers the questions
	// people actually type ("who was X", "what did X write", "where can I read X")
	// on the page AND emits the matching FAQPage JSON-LD, so the same facts serve
	// the reader and the answer engines from one source.
	//
	// English only, and for the same reason the Quotes link above is: the question
	// phrasings are hand-written English, and the derived answers lean on English
	// sentence shapes. Under any other locale the block (and its structured data)
	// simply doesn't render, rather than showing untranslated strings — the
	// established pattern on this page, not a hardcoded string that leaks into
	// every language.
	// Oxford-comma conjunction ("a", "a and b", "a, b, and c"). The block is
	// English-gated, so the fixed 'en' locale matches the surrounding copy.
	const enList = new Intl.ListFormat('en', { style: 'long', type: 'conjunction' });
	const joinList = (xs: string[]) => enList.format(xs);

	const faq = $derived.by<{ q: string; a: string }[]>(() => {
		if (getLang() !== 'en') return [];
		const name = author.name;
		const items: { q: string; a: string }[] = [];

		// "Who was …" — the opening of the biography, cut to a sentence boundary
		// (truncateMeta does exactly that). Skipped when this writer has no bio in
		// the library yet.
		const who = truncateMeta(bioStripped || author.bio || '', 320);
		if (who) items.push({ q: `Who was ${name}?`, a: who });

		if (author.books.length) {
			const titles = author.books.map((b) => b.title);
			items.push({
				q: `What did ${name} write?`,
				a: `${name} wrote ${joinList(titles)} — ${titles.length === 1 ? 'free to read' : 'all free to read'} on Ochorus.`
			});
		}

		if (author.birth_year && author.death_year)
			items.push({ q: `When did ${name} live?`, a: `${name} lived from ${author.birth_year} to ${author.death_year}.` });
		else if (author.birth_year)
			items.push({ q: `When was ${name} born?`, a: `${name} was born in ${author.birth_year}.` });

		if (author.topics.length)
			items.push({
				q: `What did ${name} write about?`,
				a: `${name}’s work centres on ${joinList(author.topics.map((tp) => tp.title))}.`
			});

		items.push({
			q: `Where can I read ${name}’s books online?`,
			a: `Every available work by ${name} can be read free on Ochorus — in your browser, without an account.`
		});

		return items;
	});
	// Two entries is the floor: a lone Q&A isn't an "FAQ", and a one-item FAQPage
	// is noise in the markup.
	const showFaq = $derived(faq.length >= 2);
	const faqLd = $derived(showFaq ? faqPage(faq) : null);
</script>

<Seo
	title="{heading} — Ochorus"
	{description}
	{canonical}
	{hreflang}
	ogType="profile"
	{ogImage}
	ogImageAlt={author.photo_url ? `${t('a11y.portraitOf')} ${author.name}` : ''}
	structuredData={[personLd, worksLd, crumbsLd, faqLd].filter((x): x is string => x != null)}
/>

<div class="page-col px-5 py-10">
	<!-- Focus mode strips the page back to the life itself. Everything here is
	     context around the biography — portrait, timeline, epigraph, shelves,
	     contemporaries — and it is exactly what someone reading eleven minutes
	     of prose wants out of the way. -->
	{#if !readerUi.focus}
	<Breadcrumb items={crumbs} />

	<!-- Wraps on a phone. The action row was already overflowing the viewport by
	     ~99px with three buttons (it is `shrink-0` beside a name that can be two
	     lines long); text settings and focus would have pushed it further. -->
	<header class="flex flex-wrap items-center gap-x-5 gap-y-4">
		{#if author.photo_url}
			<img
				src={author.photo_url}
				alt="{t('a11y.portraitOf')} {author.name}"
				class="h-24 w-24 shrink-0 rounded-full border border-border object-cover shadow-sm"
				style="filter: grayscale(1); object-position: {portraitPosition(author.slug)}"
			/>
		{:else}
			<span
				class="font-display flex h-24 w-24 shrink-0 items-center justify-center rounded-full bg-accent-soft text-h1 font-semibold text-accent"
			>
				{initials(author.name)}
			</span>
		{/if}
		<!-- basis-64 + flex-1: the heading is now a sentence, not a name, and at its
		     natural width it no longer fits beside the portrait — the wrapping
		     header would drop the portrait onto its own line. Letting this column
		     shrink keeps them side by side, while the 16rem basis still wraps on a
		     phone. -->
		<div class="min-w-0 flex-1 basis-64">
			<h1 class="text-h1" dir="auto">{heading}</h1>
			{#if summaryBits.length}
				<p class="mt-1 text-body text-muted">
					{#each summaryBits as bit, i (i)}{#if i > 0}<span class="opacity-50"> · </span>{/if}{bit}{/each}
				</p>
			{/if}
		</div>
		<div class="ms-auto flex flex-wrap items-center gap-2">
			<!-- Search this author's works. A reader who has read one Murray book
			     and half-remembers a phrase from another is on this page, and
			     until now their only option was the whole library. -->
			<a
				href={localizeHref(scopedSearchHref('author', author.slug))}
				class="btn btn-sm btn-ghost shrink-0">{t('search.inAuthor')}</a
			>
			<!-- Shown only when a person has approved quotations for this writer,
			     and only to English readers: the page is English (the quotations
			     are lifted from the English works and each citation names an
			     English chapter), so offering it under a locale prefix would
			     promise a page that does not exist. Un-localized href for the
			     same reason. This link is also what keeps the quote page off the
			     list of pages reachable only from the sitemap. -->
			{#if author.quote_count && getLang() === 'en'}
				<a href={`/quotes/${author.slug}/`} class="btn btn-sm btn-ghost shrink-0">Quotes</a>
			{/if}
			<FavoriteButton kind="author" slug={author.slug} showLabel />
			{#if listen.supported && author.bio_html}
				<button
					class="btn btn-icon btn-ghost shrink-0"
					class:text-accent={listen.status !== 'idle'}
					onclick={() => (listen.status === 'idle' ? reader?.startListening() : listen.stop())}
					aria-label={t('reader.listen')}
					title={t('reader.listen')}><Icon name="headphones" size={16} /> {t('reader.listen')}</button
				>
			{/if}
			<!-- Reader affordances, shown only when there is a long-form biography to
			     read: text settings, and focus mode to strip the page back to prose. -->
			{#if author.bio_html}
				<ReaderControls />
				<button
					class="btn btn-icon btn-ghost shrink-0"
					onclick={() => readerUi.toggleFocus()}
					aria-label={t('reader.focus')}
					title={t('reader.focus')}><Icon name="maximize" size={18} /></button
				>
			{/if}
		</div>
	</header>

	<!-- Lifespan timeline: places the author in history at a glance. -->
	<LifeTimeline birthYear={author.birth_year} deathYear={author.death_year} />

	<!-- Featured pull-quote: a hook above the biography. -->
	{#if featuredQuote}
		<blockquote class="author-quote mx-auto mt-8 max-w-[40rem]">{featuredQuote}</blockquote>
	{/if}

	<!-- Where to start + total reading time. -->
	{#if startWork || totalWords}
		<div
			class="mx-auto mt-6 flex max-w-[40rem] flex-wrap items-center gap-x-5 gap-y-1.5 rounded-card border border-border bg-surface px-4 py-3 text-small"
		>
			{#if startWork}
				<span class="text-muted">
					{t('author.startWith')}
					<a
						href={localizeHref(`/books/${startWork.slug}`)}
						class="font-semibold text-accent hover:underline">{startWork.title}</a
					>
				</span>
			{/if}
			{#if totalWords}
				<span class="text-muted sm:ms-auto">{t('author.allWorks')} · {readingTime(totalWords)}</span>
			{/if}
		</div>
	{/if}
	{/if}

	<!-- Biography. The band — not the page — carries the reader's CSS variables,
	     so the width/size/typeface controls govern the prose while the portrait,
	     book grid and contemporaries keep the page's own layout. `bioLabels`
	     rides along on the same element: custom properties inherit, so the
	     prayer-callout ::before labels reach the injected HTML. -->
	{#if author.bio_html}
		<div
			class="mx-auto mt-8"
			style="{readerPrefs.style}; {bioLabels}; max-width: var(--reading-measure)"
		>
			<Reader
				bind:this={reader}
				kind="bio"
				slug={author.slug}
				order={BIO_CHAPTER_ORDER}
				language={data.language as string}
				html={author.bio_html}
				class="bio"
				{cite}
				listenTitle={author.name}
				listenArtist={t('bios.eyebrow')}
				bind:body={bioEl}
				bind:frac
				headerOffset={0}
			/>
		</div>
	{:else if author.bio}
		<p class="mt-6 text-body leading-relaxed text-muted">{author.bio}</p>
	{/if}

	{#if !readerUi.focus}
	<!-- Topical shelves this author appears in: cross-navigation into browse. -->
	{#if author.topics.length}
		<div class="mx-auto mt-8 flex max-w-[40rem] flex-wrap items-center gap-2">
			<span class="eyebrow text-muted">
				{t('author.themes')}
			</span>
			{#each author.topics as topic (topic.slug)}
				<a
					href={localizeHref(`/topics/${topic.slug}`)}
					class="tag"
				>
					{topic.title}
				</a>
			{/each}
		</div>
	{/if}

	<!-- Books -->
	{#if author.books.length}
		<section class="mt-14">
			<h2 class="section-label">
				{t('author.booksBy')} {author.name}
				<span class="text-small font-normal count">({author.books.length})</span>
			</h2>
			<!-- Wider cards than .book-grid: one writer's shelf is a handful of
			     books, and six-across would set them as thumbnails. -->
			<div class="grid grid-cols-2 gap-5 sm:grid-cols-3 lg:grid-cols-4">
				{#each author.books as book (book.slug)}
					<BookCard {book} />
				{/each}
			</div>
		</section>
	{/if}

	<!-- Sermons -->
	{#if author.sermons.length}
		<section class="mt-14">
			<h2 class="section-label">
				{t('author.sermonsBy')} {author.name}
				<span class="text-small font-normal count">({author.sermons.length})</span>
			</h2>
			<!-- The shared card, not a hand-rolled list: this one used to compute
			     its own length with Math.round(word_count / 200), which could
			     disagree with the figure on the sermon's own page. -->
			<div class="grid gap-3 sm:grid-cols-2">
				{#each author.sermons as sermon (sermon.slug)}
					<SermonCard {sermon} />
				{/each}
			</div>
		</section>
	{/if}

	<!-- Also appears in: books this person is FOUND IN but did not write
	     (BookPerson) — an anthology or a life that features them. Book cards, not
	     person cards, and showAuthor so it's clear whose work it is. -->
	{#if author.appears_in?.length}
		<section class="mt-14">
			<h2 class="section-label">{t('author.appearsIn')}</h2>
			<div class="grid grid-cols-2 gap-5 sm:grid-cols-3 lg:grid-cols-4">
				{#each author.appears_in as book (book.slug)}
					<BookCard {book} showAuthor />
				{/each}
			</div>
		</section>
	{/if}

	{#if !author.books.length && !author.sermons.length && !author.appears_in?.length}
		<div class="mt-10"><EmptyState message={t('author.empty')} /></div>
	{/if}

	<!-- Frequently asked questions, derived from the page's own facts (see `faq`
	     in the script). Renders only with two or more entries, and only in
	     English — the same gate as the Quotes link. The visible accordion and the
	     FAQPage JSON-LD are built from one array, so they cannot disagree. -->
	{#if showFaq}
		<section class="mt-14 mx-auto max-w-[40rem]">
			<!-- Literal, not a t() key: the section only renders under English (see
			     `faq`), so a localized heading over hardcoded-English questions would
			     be an orphan key no locale ever shows. -->
			<h2 class="section-label">Common questions</h2>
			<div class="faq-list">
				{#each faq as item, i (i)}
					<details class="faq-item" open={i === 0}>
						<summary>{item.q}</summary>
						<p class="faq-a">{item.a}</p>
					</details>
				{/each}
			</div>
		</section>
	{/if}

	<!-- More lives to explore: nearest contemporaries by era. -->
	{#if contemporaries.length}
		<section class="mt-16 border-t border-border pt-8">
			<h2 class="section-label">{t('author.moreLives')}</h2>
			<div class="grid grid-cols-2 gap-4 sm:grid-cols-3">
				{#each contemporaries as c (c.slug)}
					<PersonCard person={c} />
				{/each}
			</div>
		</section>
	{/if}

	<!-- Portrait credit. Rendered only when the portrait is a Creative Commons
	     image whose licence requires attribution; a public-domain portrait
	     leaves `photo_attribution` blank and shows nothing here. Sits with the
	     page context (hidden in focus mode), a quiet colophon beneath the works. -->
	{#if author.photo_attribution}
		<p class="mt-12 border-t border-border pt-4 text-micro text-muted">
			{t('author.portraitCredit')}:
			{#if author.photo_source_url}
				<a
					href={author.photo_source_url}
					class="hover:text-accent hover:underline"
					target="_blank"
					rel="noreferrer">{author.photo_attribution}</a
				>
			{:else}
				{author.photo_attribution}
			{/if}
		</p>
	{/if}
	{/if}
</div>

{#if readerUi.focus}
	<FocusExit />
{/if}

<!-- Time remaining in the biography. Gated on the prose actually being in
     view: this is a page with a book grid and contemporaries below, so a pill
     claiming "N min left" while scrolling those would be measuring the wrong
     thing. <Reader> supplies `frac` for the prose alone. -->
{#if !readerUi.focus && listen.status === 'idle' && frac > 0.01 && frac < 0.99}
	<div class="min-left" aria-hidden="true">{minutesLeft} {t('sermon.minLeft')}</div>
{/if}

<!-- Bookmark the spot. It FLOATS rather than sitting with the other reader
     affordances in the header, and that is the whole point: this page's header
     scrolls away (unlike the sermon reader's sticky bar), so a control up there
     can only be reached by scrolling back to the top — at which point "the
     paragraph at the top of the viewport" is paragraph one, every time. The
     button would have looked right and saved the wrong place on every click.

     Gated on `frac` exactly like the pill above, for the same reason: this page
     continues into a book grid and contemporaries, and a bookmark control has
     nothing to point at once the prose is behind you. -->
{#if author.bio_html && frac > 0.01 && frac < 0.99}
	<button
		class="bio-bookmark"
		class:is-set={currentBookmarked}
		onclick={toggleBookmark}
		aria-label={t('reader.bookmark')}
		title={t('reader.bookmark')}
		aria-pressed={currentBookmarked}><Icon name="bookmark" size={18} /></button
	>
{/if}

<style>
	/* Floating bookmark control for the biography. Deliberately mirrors
	   `.min-left` (app.css) — same corner treatment, same z-index, same
	   translucency — so the two pills that appear while reading a bio read as
	   one family. It sits at the inline end rather than centred, because
	   `.min-left` already owns the centre and this one is tappable. Logical
	   properties throughout: Arabic is a routed locale. */
	.bio-bookmark {
		position: fixed;
		bottom: 1rem;
		inset-inline-end: 1rem;
		z-index: 30;
		display: flex;
		align-items: center;
		justify-content: center;
		width: 2.5rem;
		height: 2.5rem;
		border-radius: 9999px;
		border: 1px solid var(--border);
		background: color-mix(in srgb, var(--bg) 85%, transparent);
		backdrop-filter: blur(6px);
		color: var(--muted);
	}
	.bio-bookmark:hover {
		color: var(--text);
	}
	.bio-bookmark.is-set {
		color: var(--accent);
		border-color: var(--accent);
	}

	/* Derived FAQ accordion. Native <details> so it works with no JS and during
	   prerender; the marker is replaced with a +/− that flips on [open]. */
	.faq-list {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}
	.faq-item {
		border: 1px solid var(--border);
		border-radius: var(--radius-card);
		background: var(--surface);
		overflow: hidden;
	}
	.faq-item summary {
		cursor: pointer;
		list-style: none;
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.85rem 1rem;
		font-family: var(--font-display);
		font-weight: 600;
		font-size: var(--fs-body);
		color: var(--text);
	}
	.faq-item summary::-webkit-details-marker {
		display: none;
	}
	.faq-item summary::after {
		content: '+';
		margin-inline-start: auto;
		font-size: var(--fs-h3);
		line-height: 1;
		font-weight: 400;
		color: var(--accent);
	}
	.faq-item[open] summary::after {
		content: '−';
	}
	.faq-a {
		margin: 0;
		padding: 0 1rem 0.95rem;
		color: var(--muted);
		font-size: var(--fs-body);
		line-height: 1.6;
	}

	/* Featured header pull-quote — a hook above the biography. */
	.author-quote {
		font-family: var(--font-display);
		font-style: italic;
		font-size: var(--fs-h2);
		line-height: 1.4;
		color: var(--text);
		border-inline-start: 3px solid var(--gold);
		padding-block: 0.1em;
		padding-inline: 1.25rem 0;
	}
	.author-quote::before {
		content: '“';
	}
	.author-quote::after {
		content: '”';
	}

	/* Long-form biography styling. Targets the injected {@html} via :global.
	   Pull-quotes and prayer callouts stand out.

	   Type is NOT set here any more: the element is `.reading.bio`, so size,
	   leading, typeface and colour come from the reader's CSS variables and the
	   text-settings control moves them. Re-declaring them here would silently
	   win over the reader on this one surface. */
	:global(.bio p) {
		margin: 0 0 1.15em;
	}
	:global(.bio h2) {
		font-family: var(--font-display);
		font-size: var(--fs-h2);
		font-weight: 600;
		line-height: 1.25;
		margin: 1.9em 0 0.55em;
	}
	:global(.bio a) {
		color: var(--accent);
	}

	/* Pull-quote: a called-out saying, visually distinct. */
	:global(.bio blockquote) {
		margin: 1.7em 0;
		padding-block: 0.1em;
		padding-inline: 1.25rem 0;
		border-inline-start: 3px solid var(--gold);
		font-size: var(--fs-h2);
		line-height: 1.45;
		font-style: italic;
		color: var(--text);
	}
	:global(.bio blockquote p) {
		margin: 0;
	}
	:global(.bio blockquote cite) {
		display: block;
		margin-top: 0.55em;
		font-size: var(--fs-small);
		font-style: normal;
		color: var(--muted);
	}

	/* Prayer callout: highlights a key time of prayer. `.answered` marks an
	   answer to prayer with the indigo accent instead of gold. */
	:global(.bio .prayer) {
		margin: 1.7em 0;
		padding: 1rem 1.2rem;
		border-radius: var(--radius-card);
		background: color-mix(in srgb, var(--gold) 12%, transparent);
		border: 1px solid color-mix(in srgb, var(--gold) 32%, transparent);
	}
	:global(.bio .prayer > *:last-child) {
		margin-bottom: 0;
	}
	:global(.bio .prayer)::before {
		content: '✦ ' var(--label-in-prayer, 'In prayer');
		display: block;
		margin-bottom: 0.5rem;
		font-family: var(--font-sans);
		font-size: var(--fs-micro);
		font-weight: 600;
		letter-spacing: 0.08em;
		text-transform: uppercase;
		color: var(--gold);
	}
	:global(.bio .prayer.answered) {
		background: var(--accent-soft);
		border-color: var(--accent-soft-border);
	}
	:global(.bio .prayer.answered)::before {
		content: '✦ ' var(--label-answered, 'Answer to prayer');
		color: var(--accent);
	}
</style>
