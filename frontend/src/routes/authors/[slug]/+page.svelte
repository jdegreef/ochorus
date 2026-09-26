<script lang="ts">
	import { hydrateSrc } from '$lib/hydrateSrc';
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
	import { scrollSpy, jumpToSection } from '$lib/scrollSpy.svelte';
	import { localizeHref } from '$lib/href';
	import Breadcrumb from '$lib/components/Breadcrumb.svelte';
	import { scopedSearchHref } from '$lib/searchState';
	import { shareCard } from '$lib/coverArt';
	import { initials, portraitPosition, portraitSrcset } from '$lib/portraits';
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
	import ArticleLinkCard from '$lib/components/ArticleLinkCard.svelte';
	import FavoriteButton from '$lib/components/FavoriteButton.svelte';
	import ShareButton from '$lib/components/ShareButton.svelte';
	import Seo from '$lib/components/Seo.svelte';
	import LifeTimeline from '$lib/components/LifeTimeline.svelte';
	import Reader from '$lib/components/Reader.svelte';
	import ReaderControls from '$lib/components/ReaderControls.svelte';
	import SermonCard from '$lib/components/SermonCard.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import { onMount } from 'svelte';
	import BookCover from '$lib/components/BookCover.svelte';
	import ProgressBar from '$lib/components/ProgressBar.svelte';
	import { allProgress, isFinished } from '$lib/progress';
	import type { BookSummary } from '$lib/library-public';

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
	// A bio, when this locale has one, is used as-is. When it doesn't, the localized
	// metaFallback sentence is enriched with the same era + work counts the header
	// shows (summaryBits — already localized), so a bio-less author page still offers
	// the SERP something concrete rather than a bare "free classic Christian books"
	// line. No new catalogue string; the counts matter most on translated pages,
	// where a localized bio is most often absent.
	const description = $derived.by(() => {
		if (author.bio) return truncateMeta(author.bio);
		const base = t('author.metaFallback').replace('%name%', author.name);
		return truncateMeta(summaryBits.length ? `${base} ${summaryBits.join(' · ')}.` : base);
	});
	// A portrait, else the first book's landscape share card — never its raw
	// `cover_url`, which for a plate is an `.svg` scrapers refuse and for a
	// painting is a picture with no title on it (see `shareCard`).
	const bookCard = $derived(author.books[0] ? shareCard(author.books[0]) : null);
	const ogImage = $derived(
		author.photo_url ? absUrl(author.photo_url) : bookCard ? absUrl(bookCard.url) : ''
	);

	const personLd = $derived(
		jsonLd({
			'@context': 'https://schema.org',
			'@type': 'Person',
			name: author.name,
			description: author.bio || undefined,
			// The PERSON's image: a portrait or nothing. The share card falls
			// back to a book cover, which is right for a link preview and wrong
			// here — structured data would be claiming the cover depicts them.
			image: author.photo_url ? absUrl(author.photo_url) : undefined,
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

	// The read card: a reader partway through one of this author's books picks
	// it up here ("Continue reading" — the book page's card); anyone else gets
	// the "New to X? Start with …" suggestion in the same card. Progress is
	// client-only, so the prerendered page and a first visit show the latter.
	let resumeBook = $state<{ book: BookSummary; order: number } | null>(null);
	$effect(() => {
		const bySlug = new Map(author.books.map((b) => [b.slug, b]));
		const rec = allProgress().find(
			(r) => r.kind === 'book' && bySlug.has(r.slug) && !isFinished(r.slug)
		);
		resumeBook = rec ? { book: bySlug.get(rec.slug)!, order: rec.order } : null;
	});
	const cardBook = $derived(resumeBook?.book ?? startWork);

	// A featured pull-quote for the header: the first <blockquote> in the bio.
	// Regex, not the DOM, so it works during prerender too. Absent / too-short
	// quotes just don't show. The bio's own <cite> is kept as the attribution
	// beneath the quote (its leading dash trimmed) rather than discarded.
	const featuredQuote = $derived.by<{ text: string; cite: string }>(() => {
		const m = (author.bio_html || '').match(/<blockquote[^>]*>([\s\S]*?)<\/blockquote>/i);
		if (!m) return { text: '', cite: '' };
		const inner = m[1];
		const citeMatch = inner.match(/<cite[^>]*>([\s\S]*?)<\/cite>/i);
		const cite = citeMatch
			? stripHtml(citeMatch[1])
					.replace(/\s+/g, ' ')
					.replace(/^[—–-]\s*/, '')
					.trim()
			: '';
		const text = stripHtml(inner.replace(/<cite[\s\S]*?<\/cite>/i, ''))
			.replace(/\s+/g, ' ')
			.trim();
		if (text.length < 20) return { text: '', cite: '' };
		const clipped = text.length > 220 ? text.slice(0, 217).trimEnd() + '…' : text;
		return { text: clipped, cite };
	});

	// The Q&A band at the foot of the page: an editorial set, hand-written and
	// verified per author, served by the API in the requested language only —
	// empty when this locale has none (the no-fallback rule the bio follows, so
	// it is NOT gated here; the API has already decided the language). Every
	// biography now carries a set; there is no longer a page-derived fallback —
	// a future author added before its set is written simply shows no Q&A band,
	// which is the honest answer, rather than a generic "read X free" stand-in.
	// The visible accordion and the FAQPage JSON-LD below both read this one
	// array, so they can never disagree.
	const faq = $derived<{ q: string; a: string }[]>(author.faq ?? []);
	// Two entries is the floor: a lone Q&A isn't an "FAQ", and a one-item FAQPage
	// is noise in the markup.
	const showFaq = $derived(faq.length >= 2);
	const faqLd = $derived(showFaq ? faqPage(faq) : null);

	// On-page jump navigation over the substantial sections. Each entry names a
	// section `id` stamped on the markup below. Labels reuse existing localized
	// strings, so no new visible copy is introduced; "Questions" rides `showFaq`,
	// so it never appears without the section it points at (in a locale whose Q&A
	// is not yet translated the API returns none, and both drop out together).
	const navItems = $derived(
		[
			author.bio_html || author.bio ? { id: 'bio', label: t('articles.kindBiography') } : null,
			author.books.length ? { id: 'books', label: t('nav.books') } : null,
			author.sermons.length ? { id: 'sermons', label: t('nav.sermons') } : null,
			author.articles?.length ? { id: 'articles', label: t('nav.articles') } : null,
			showFaq ? { id: 'faq', label: 'Questions' } : null
		].filter((x): x is { id: string; label: string } => x != null)
	);
	// Below two targets there is nothing to jump between.
	const showSubnav = $derived(navItems.length >= 2);

	// The bar's measured height feeds `--pinned-offset` (set on the page column),
	// the same contract the biographies index uses so anchored sections clear both
	// the app nav and this bar. Mirrors +layout's navH measurement.
	let subnavH = $state(0);

	// Scroll-spy: light the link for whatever section sits in the band just under
	// the pinned bars. The shared helper re-observes when the target set changes
	// (empty while the sub-nav is hidden). No-JS / prerender shows the bar with
	// nothing lit — the links still jump.
	const spy = scrollSpy(() => (showSubnav ? navItems.map((n) => n.id) : []));

	// Smooth-jump to a section and light it at once, so the tap feels immediate
	// rather than waiting on the scroll-spy to catch up. The landing offset lives
	// in CSS (`--pinned-offset` + the subnav-link scroll-margin below), so
	// jumpToSection just scrolls; the hash stays ours to set.
	function jumpTo(e: MouseEvent, id: string) {
		e.preventDefault();
		spy.set(id);
		jumpToSection(id);
		history.replaceState(null, '', `#${id}`);
	}
</script>

<Seo
	title="{heading} — Ochorus"
	{description}
	{canonical}
	{hreflang}
	ogType="profile"
	{ogImage}
	ogImageWidth={author.photo_url ? undefined : bookCard?.width}
	ogImageHeight={author.photo_url ? undefined : bookCard?.height}
	ogImageAlt={author.photo_url
		? `${t('a11y.portraitOf')} ${author.name}`
		: bookCard
			? `${t('a11y.coverOf')} ${author.books[0].title}`
			: ''}
	structuredData={[personLd, worksLd, crumbsLd, faqLd].filter((x): x is string => x != null)}
/>

<!-- --pinned-offset: how far down the first pixel unobstructed by BOTH the app
     nav and this page's own sticky jump-bar is; anchored sections read it for
     scroll-margin so a jump lands below the bars. Same contract as the
     biographies index. -->
<div class="page-col px-5 py-10" style="--pinned-offset: calc(var(--appnav-h, 0px) + {subnavH}px)">
	<!-- Focus mode strips the page back to the life itself. Everything here is
	     context around the biography — portrait, timeline, epigraph, shelves,
	     contemporaries — and it is exactly what someone reading eleven minutes
	     of prose wants out of the way. -->
	{#if !readerUi.focus}
	<Breadcrumb items={crumbs} />

	<!-- A CENTRED masthead stack: portrait, name, era/counts, then the action row,
	     all sharing the same reading column as the timeline, quote and biography
	     below. The page used to left-align a full-width header over a centred body,
	     so the eye jumped margins and a wide empty gutter opened beside the prose;
	     one centred column removes both. The action row wraps and stays centred on
	     a phone. -->
	<header class="mx-auto flex max-w-[40rem] items-center gap-4 sm:gap-5">
		{#if author.photo_url}
			{@const source = { src: author.photo_url, srcset: portraitSrcset(author.photo_url) }}
			<img
				src={source.src}
				srcset={source.srcset}
				use:hydrateSrc={source}
				sizes="112px"
				width="112"
				height="112"
				alt="{t('a11y.portraitOf')} {author.name}"
				class="h-20 w-20 shrink-0 rounded-full border border-border object-cover shadow-sm sm:h-28 sm:w-28"
				style="filter: grayscale(1); object-position: {portraitPosition(author.slug)}"
			/>
		{:else}
			<span
				class="font-display flex h-20 w-20 shrink-0 items-center justify-center rounded-full bg-accent-soft text-h1 font-semibold text-accent sm:h-28 sm:w-28"
			>
				{initials(author.name)}
			</span>
		{/if}
		<div class="min-w-0">
		<h1 class="text-h1" dir="auto">{heading}</h1>
		{#if summaryBits.length}
			<p class="mt-1.5 text-body text-muted">
				<!-- The separator as an expression: literal spaces at an {#if} boundary are
				     compiler-trimmed ("1828–1917·12 books"). -->
				{#each summaryBits as bit, i (i)}{#if i > 0}<span class="opacity-50">{' · '}</span>{/if}{bit}{/each}
			</p>
		{/if}
		</div>
	</header>

	<!-- The read card (shared .read-card, as on the book and plan pages): pick up
	     one of this author's books where you left off, or — first visit, and the
	     prerender — where to start, with the total reading time. -->
	{#if cardBook}
		<div class="read-card mx-auto mt-6 max-w-[40rem]">
			<div class="flex min-w-0 flex-1 items-center gap-3">
				<div class="w-12 shrink-0"><BookCover book={cardBook} rounded="rounded-[3px]" /></div>
				<div class="min-w-0 flex-1">
					{#if resumeBook}
						<p class="text-small text-muted">
							{t('continue.title')} · {t('book.onChapter')
								.replace('%n%', String(resumeBook.order))
								.replace('%t%', String(cardBook.chapter_count))}
						</p>
						<p class="read-card-title" dir="auto">{cardBook.title}</p>
						<div class="mt-2">
							<ProgressBar
								percent={cardBook.chapter_count
									? ((resumeBook.order - 1) / cardBook.chapter_count) * 100
									: 0}
								label="{cardBook.title}: {t('book.onChapter')
									.replace('%n%', String(resumeBook.order))
									.replace('%t%', String(cardBook.chapter_count))}"
							/>
						</div>
					{:else}
						<p class="text-small">
							<span class="font-medium text-accent"
								>{t('author.newToAuthor').replace('%name%', author.name)}</span
							>
							<span class="text-muted">{t('author.startWith')}</span>
						</p>
						<p class="read-card-title" dir="auto">{cardBook.title}</p>
						{#if totalWords}
							<p class="text-small text-muted">{t('author.allWorks')} · {readingTime(totalWords)}</p>
						{/if}
					{/if}
				</div>
			</div>
			<div class="read-card-cta">
				<a
					href={localizeHref(`/books/${cardBook.slug}/${resumeBook ? resumeBook.order : 1}`)}
					class="btn btn-primary">{resumeBook ? t('book.continue') : t('book.beginReading')}</a
				>
			</div>
		</div>
	{/if}

	<!-- The page's own actions — keep, share, the writer's quotations, search
	     their works — as the book page's action row (an icon strip when narrow).
	     The biography's reading tools live with the biography below. -->
	<div class="action-host mx-auto mt-3 max-w-[40rem]">
		<div class="action-strip">
			<FavoriteButton kind="author" slug={author.slug} showLabel />
			<ShareButton url={canonical} title={author.name} showLabel />
			<!-- Shown only when a person has approved quotations for this writer,
			     and only to English readers: the page is English (the quotations
			     are lifted from the English works and each citation names an
			     English chapter), so offering it under a locale prefix would
			     promise a page that does not exist. Un-localized href for the
			     same reason. This link is also what keeps the quote page off the
			     list of pages reachable only from the sitemap. -->
			{#if author.quote_count && getLang() === 'en'}
				<a href={`/quotes/${author.slug}/`} class="btn btn-sm btn-ghost"
					><Icon name="quote" size={16} /><span>Quotes</span></a
				>
			{/if}
			<!-- Search this author's works — the real search, scoped to them. -->
			<a
				href={localizeHref(scopedSearchHref('author', author.slug))}
				class="btn btn-sm btn-ghost"
				aria-label={t('search.inAuthor')}
				title={t('search.inAuthor')}><Icon name="search" size={16} /><span>{t('nav.search')}</span></a
			>
		</div>
	</div>

	<!-- On-page jump navigation. Sits directly under the masthead's action row —
	     a full-width section rule the reader meets before the timeline — then pins
	     under the app nav (`--appnav-h`) on scroll; its measured height feeds
	     `--pinned-offset` above. Hidden in focus mode with the rest of the page
	     context. Only shown when there are ≥2 sections to move between. -->
	{#if showSubnav}
		<nav
			bind:clientHeight={subnavH}
			class="author-subnav sticky z-20 mt-6 border-b border-border bg-bg"
			style="top: var(--appnav-h, 0px)"
			aria-label={t('a11y.pageSections')}
		>
			<ul class="flex justify-center gap-1 overflow-x-auto">
				{#each navItems as item (item.id)}
					<li>
						<a
							href="#{item.id}"
							class="subnav-link"
							class:is-active={spy.active === item.id}
							aria-current={spy.active === item.id ? 'true' : undefined}
							onclick={(e) => jumpTo(e, item.id)}>{item.label}</a
						>
					</li>
				{/each}
			</ul>
		</nav>
	{/if}

	<!-- The biography's heading carries its own reading tools — Listen, text
	     settings, focus mode apply to the life story, not to the page, so they
	     sit with it rather than among the page actions above. -->
	{#if author.bio_html || author.bio}
		<div id="bio" class="jump-anchor bio-head mx-auto mt-8 flex max-w-[40rem] items-center gap-3">
			<h2 class="font-display text-h2 font-semibold">{t('articles.kindBiography')}</h2>
			{#if author.bio_html}
				<div class="reader-tools ms-auto shrink-0">
					{#if listen.supported}
						<button
							class="btn btn-icon btn-ghost"
							class:text-accent={listen.status !== 'idle'}
							onclick={() => (listen.status === 'idle' ? reader?.startListening() : listen.stop())}
							aria-label={t('reader.listen')}
							title={t('reader.listen')}><Icon name="headphones" size={16} /></button
						>
					{/if}
					<ReaderControls />
					<button
						class="btn btn-icon btn-ghost"
						onclick={() => readerUi.toggleFocus()}
						aria-label={t('reader.focus')}
						title={t('reader.focus')}><Icon name="maximize" size={18} /></button
					>
				</div>
			{/if}
		</div>
	{/if}

	<!-- Lifespan timeline: their own milestones when curated, else the bare
	     lifespan bar (see LifeTimeline). -->
	<LifeTimeline
		birthYear={author.birth_year}
		deathYear={author.death_year}
		milestones={author.milestones}
		labels={getLang() === 'en'}
	/>

	<!-- Featured pull-quote: a hook above the biography, carrying the bio's own
	     attribution beneath it. -->
	{#if featuredQuote.text}
		<figure class="mx-auto mt-8 max-w-[40rem]">
			<blockquote class="author-quote">{featuredQuote.text}</blockquote>
			{#if featuredQuote.cite}
				<figcaption class="author-quote-cite">{featuredQuote.cite}</figcaption>
			{/if}
		</figure>
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
		<section id="books" class="jump-anchor mx-auto mt-12 max-w-[40rem]">
			<h2 class="section-heading">
				{t('author.booksBy')} {author.name}
				<span class="text-small font-normal count">({author.books.length})</span>
			</h2>
			<!-- Three across at most: the page is now one reading-width column, so a
			     writer's shelf sits as a handful of real covers, not a thumbnail grid. -->
			<div class="grid grid-cols-2 gap-5 sm:grid-cols-3">
				{#each author.books as book (book.slug)}
					<BookCard {book} />
				{/each}
			</div>
		</section>
	{/if}

	<!-- Sermons -->
	{#if author.sermons.length}
		<section id="sermons" class="jump-anchor mx-auto mt-12 max-w-[40rem]">
			<h2 class="section-heading">
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
		<section class="mx-auto mt-12 max-w-[40rem]">
			<h2 class="section-heading">{t('author.appearsIn')}</h2>
			<div class="grid grid-cols-2 gap-5 sm:grid-cols-3">
				{#each author.appears_in as book (book.slug)}
					<BookCard {book} showAuthor />
				{/each}
			</div>
		</section>
	{/if}

	{#if !author.books.length && !author.sermons.length && !author.appears_in?.length}
		<div class="mt-10"><EmptyState message={t('author.empty')} /></div>
	{/if}

	<!-- Articles that name this person (the API's `articles` /
	     articles_for_author, which documents the rule). The mirror of the book
	     page's Reader's guide: an article reachable only from the /articles hub
	     sits too deep in the link graph to earn a crawl, and an author page is
	     crawled far more often. Per-language — an untranslated locale gets an
	     empty list and no section at all. Below the works, because these are
	     writing ABOUT this person, not BY them. -->
	{#if author.articles?.length}
		<section id="articles" class="jump-anchor mx-auto mt-12 max-w-[40rem]">
			<h2 class="section-heading">
				{t('author.articlesAbout')}
				{author.name}
				<span class="text-small font-normal count">({author.articles.length})</span>
			</h2>
			<ul class="mt-3 flex flex-col gap-3">
				{#each author.articles as article (article.slug)}
					<li><ArticleLinkCard {article} cta={t('author.readArticle')} /></li>
				{/each}
			</ul>
		</section>
	{/if}

	<!-- Frequently asked questions — the editorial set for this author (see `faq`
	     in the script). Renders only with two or more entries. The visible
	     accordion and the FAQPage JSON-LD are built from one array, so they cannot
	     disagree. -->
	{#if showFaq}
		<section id="faq" class="jump-anchor mx-auto mt-12 max-w-[40rem]">
			<!-- Localized: the API serves the Q&A per locale (AuthorTranslation.faq),
			     so the heading follows the reader's language too. Reuses the same
			     `qa.sectionTitle` key the book Q&A section uses, so the two read
			     identically. -->
			<h2 class="section-heading">{t('qa.sectionTitle')}</h2>
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
		<section class="mx-auto mt-12 max-w-[40rem] border-t border-border pt-8">
			<h2 class="section-heading">{t('author.moreLives')}</h2>
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
		<p class="mx-auto mt-12 max-w-[40rem] border-t border-border pt-4 text-micro text-muted">
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

	/* Reading tools as a segmented control: one bordered cluster with hairline
	   dividers, instead of three separate ghost-button pills. No `overflow:hidden`
	   — ReaderControls' text-settings popover is position:absolute and would be
	   clipped by it — so the group rounds its own outer corners on the end tools
	   instead. The inner buttons (and ReaderControls' own trigger, reached with
	   :global) drop their border and radius; the group carries them. */
	/* The Biography heading row: a section rule, like .section-heading, with the
	   reading tools at its end. */
	.bio-head {
		padding-bottom: 0.4rem;
		border-bottom: 1px solid var(--border);
	}
	.reader-tools {
		display: inline-flex;
		align-items: stretch;
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
	}
	/* Each tool fills its segment: no top/bottom/end border and no radius of its
	   own. The LEADING (inline-start) border is the divider between tools — every
	   tool carries it, and the first tool drops it below. `:global` reaches
	   ReaderControls' own trigger, a child-component element this component's
	   scope class never lands on (a plain scoped selector skipped it). */
	.reader-tools :global(.btn) {
		border-block: 0;
		border-inline-end: 0;
		border-radius: 0;
		border-inline-start: 1px solid var(--border);
	}
	/* First tool: no leading divider, and it carries the group's start corners.
	   Handles both a direct button (Listen) and ReaderControls' nested button. */
	.reader-tools > :first-child.btn,
	.reader-tools > :first-child :global(.btn) {
		border-inline-start: 0;
		border-start-start-radius: calc(var(--radius-sm) - 1px);
		border-end-start-radius: calc(var(--radius-sm) - 1px);
	}
	/* Last tool (always the focus button) carries the group's end corners. */
	.reader-tools > :last-child.btn,
	.reader-tools > :last-child :global(.btn) {
		border-start-end-radius: calc(var(--radius-sm) - 1px);
		border-end-end-radius: calc(var(--radius-sm) - 1px);
	}

	/* Jump-nav targets clear both pinned bars when linked to. `--pinned-offset`
	   (app nav + the sticky sub-bar) is published on the page column; the same
	   contract the biographies index's group headings use. */
	.jump-anchor {
		scroll-margin-top: calc(var(--pinned-offset, 5rem) + 0.5rem);
	}

	/* On-page jump bar. Sits in the flow after the hero, then pins under the app
	   nav on scroll. Links are quiet tabs; the active one wears the accent and an
	   underline drawn on the shared bottom border. */
	.author-subnav {
		/* A hair of top padding so the tabs don't kiss the app nav when pinned. */
		padding-block: 0.35rem 0;
	}
	.author-subnav ul {
		margin: 0;
		padding: 0;
		list-style: none;
	}
	.subnav-link {
		display: inline-block;
		padding: 0.5rem 0.75rem;
		border-bottom: 2px solid transparent;
		margin-bottom: -1px; /* overlap the bar's own border so the underline meets it */
		font-size: var(--fs-small);
		font-weight: 500;
		white-space: nowrap;
		color: var(--muted);
		text-decoration: none;
	}
	.subnav-link:hover {
		color: var(--text);
	}
	.subnav-link.is-active {
		color: var(--accent);
		border-bottom-color: var(--accent);
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
	/* The bio's own attribution, beneath the quote and aligned with its text
	   (past the gold rule). A quiet sans line — the cites are free-form sentences,
	   not a tidy NAME · WORK, so they read as prose, not an uppercase label. */
	.author-quote-cite {
		margin-top: 0.55rem;
		padding-inline-start: 1.25rem;
		font-family: var(--font-sans);
		font-size: var(--fs-small);
		color: var(--muted);
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
	/* A gold drop cap opens the life — the first letter of the FIRST paragraph
	   only, so pull-quotes and prayer callouts keep their own opening. Sized in
	   `em` so it tracks the reader's text-size control, and floated inline-start
	   so it sits correctly under a routed RTL (Arabic) bio too. */
	:global(.bio > p:first-of-type)::first-letter {
		float: inline-start;
		font-family: var(--font-display);
		font-weight: 600;
		font-size: 3.4em;
		line-height: 0.82;
		padding-inline-end: 0.09em;
		padding-block-start: 0.02em;
		color: var(--gold);
	}
	/* …but NOT under RTL: a drop cap is a Latin/LTR flourish, and an enlarged,
	   detached initial reads as broken in Arabic's cursive script. Revert it to
	   normal prose there (higher specificity than the rule above wins). */
	:global([dir='rtl'] .bio > p:first-of-type)::first-letter {
		float: none;
		font-family: inherit;
		font-weight: inherit;
		font-size: inherit;
		line-height: inherit;
		padding: 0;
		color: inherit;
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
