<script lang="ts">
	import { hubPath } from '$lib/hubs';
	import { resumeOrderOf } from '$lib/reading-schema';
	import { chapterPath } from '$lib/editionHref';
	import { readerBookmark } from '$lib/readerBookmark.svelte';
	import FloatingBookmark from '$lib/components/FloatingBookmark.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import Arrow from '$lib/components/Arrow.svelte';
	import {
		type AuthorDetail,
		type AuthorBio,
		listAuthors,
		formatLifespan,
		hasOwnContent
	} from '$lib/library-public';
	import { SITE_URL } from '$lib/config';
	import { cssString } from '$lib/cssString';
	import { absUrl, jsonLd, breadcrumbLd, faqPage, hreflangAll, hreflangExact, stripHtml, truncateMeta, itemList, topicThings, personId } from '$lib/seo';
	import { i18n } from '$lib/i18n.svelte';
	import { firstSentence } from '$lib/firstSentence';
	import { smartQuotes } from '$lib/smartQuotes';
	import { readingTime, readingMinutes } from '$lib/reading';
	import { foldBio } from '$lib/bioFold';
	import { scrollSpy, realignHashOnMeasure, subnavOffset } from '$lib/scrollSpy.svelte';
	import { tabStrip } from '$lib/actions/tabStrip';
	import { localizeHref } from '$lib/href';
	import Breadcrumb from '$lib/components/Breadcrumb.svelte';
	import { scopedSearchHref } from '$lib/searchState';
	import { LANDSCAPE_HEIGHT, LANDSCAPE_WIDTH } from '$lib/coverArt';
	import { authorCardUrl } from '$lib/authorCard';
	import AuthorHero from '$lib/components/AuthorHero.svelte';
	import AuthorCandle from '$lib/components/AuthorCandle.svelte';
	import { listen } from '$lib/listen.svelte';
	import { getLang } from '$lib/lang.svelte';
	import { page } from '$app/stores';
	import { readerPrefs } from '$lib/readerPrefs.svelte';
	import { readerUi } from '$lib/readerUi.svelte';
	import FocusExit from '$lib/components/FocusExit.svelte';
	import { BIO_CHAPTER_ORDER } from '$lib/reading-schema';
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
	import { onMount, tick } from 'svelte';
	import { holdFlag, READING_FLAG } from '$lib/presenceFlag';
	import BookCover from '$lib/components/BookCover.svelte';
	import ProgressBar from '$lib/components/ProgressBar.svelte';
	import { allProgress, isFinished } from '$lib/progress';
	import type { BookSummary } from '$lib/library-public';

	// A page of reading text is open — here, only with a life to read (the
	// reader's Aa mounts on the same condition). app.css CANDLELIGHT.
	$effect(() => {
		if (author.bio_html) return holdFlag(document.documentElement, READING_FLAG);
	});

	const t = i18n.t;

	let { data } = $props();
	const author = $derived<AuthorDetail>(data.author);
	// The books they are found in, split by whether they are the book's lone
	// subject (`about`, from the API): a life of them heads its own section.
	const booksAbout = $derived((author.appears_in ?? []).filter((b) => b.about));
	const appearsIn = $derived((author.appears_in ?? []).filter((b) => !b.about));

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

	// --- Bookmarks ------------------------------------------------------------
	// The paragraph at the top of the screen — the single-document Reader's
	// bookmark, shared with the sermon and article pages.
	const bookmark = readerBookmark({
		kind: 'bio',
		slug: () => author.slug,
		title: () => author.name,
		reader: () => reader,
		body: () => bioEl,
		frac: () => frac
	});

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

	// The <title> names what the page actually holds — "<Name> Biography,
	// Books, and Sermons" — rather than the bare name: that is how people
	// search for a writer, and it tells a crawler what the page is. The visible
	// H1 is the person's name alone (design review #13): the long phrase read
	// as an SEO string to the person who had already arrived.
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
	// The search title carries the lifespan — "Andrew Murray (1828–1917)" is how
	// people recognise the person they searched for. (seo.fitTitle drops the
	// brand suffix if it runs long.)
	const seoTitle = $derived(
		headingKey && years
			? t(headingKey).replace('%name%', `${author.name} (${years})`)
			: heading
	);

	// What is here to read — "18 books · 2 sermons" — the hero's last fact.
	const worksBits = $derived(
		[
			author.books.length
				? `${author.books.length} ${author.books.length === 1 ? t('common.bookOne') : t('common.bookMany')}`
				: '',
			author.sermons.length
				? `${author.sermons.length} ${author.sermons.length === 1 ? t('common.sermonOne') : t('common.sermonMany')}`
				: ''
		].filter(Boolean)
	);
	// The era and the work counts, for a bio-less page's meta description.
	const summaryBits = $derived([years, ...worksBits].filter(Boolean));

	// Who they were, in one line under the name: the opening sentence of the
	// summary this locale has (there is no tagline field, and the line is not
	// written for the page). No summary, no line — and none where the page
	// prints that summary itself (no long bio in this locale), which would
	// repeat the same sentence a screen lower.
	const identity = $derived(
		author.bio_html ? smartQuotes(firstSentence(author.bio), data.language as string) : ''
	);

	// The writer's hubs as key facts: their traditions, then their place, each
	// under its own label ("Tradition", "Place") — the order the API serves.
	const hubGroups = $derived(
		(
			[
				{ label: t('bios.tradition'), hubs: (author.hubs ?? []).filter((h) => h.kind === 'tradition') },
				{ label: t('bios.place'), hubs: (author.hubs ?? []).filter((h) => h.kind !== 'tradition') }
			] as const
		).filter((g) => g.hubs.length)
	);
	// The quote page is English only (see the link in the hero's facts).
	const showQuotes = $derived(!!author.quote_count && getLang() === 'en');

	// "More lives to explore": nearest contemporaries by birth year (loaded after
	// mount; the page is prerendered). Falls back to any other authors when this
	// one has no dated birth year.
	let contemporaries = $state<AuthorBio[]>([]);

	// A reading plan built from this author's books, if there is one: "Read
	// Andrew Murray a day at a time". Chosen by the API (AuthorDetailSerializer.get_plan), so
	// it is in the prerendered page and never shifts the fold.
	const authorPlan = $derived(author.plan ?? null);
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
	// Alternates only for the locales with something of the writer's own — the
	// same rule that noindexes the rest (`thin` below) and that the sitemap's
	// author entries apply — so an indexed page never names a noindexed sibling.
	// An API running behind this build omits the field: every advertised locale.
	const hreflang = $derived(
		author.available_languages
			? hreflangExact(path, author.available_languages)
			: hreflangAll(path)
	);
	// Nothing of the writer's own in THIS language: kept out of the index.
	const thin = $derived(!hasOwnContent(author));
	// Localized, because the bio may legitimately be missing in this language and
	// a hardcoded English sentence would then become the page's meta description.
	// A bare `.slice(0, 300)` cut the bio mid-word with no ellipsis (a SERP saw
	// "…fourteen great-gr"); truncateMeta ends on a sentence or whole-word boundary
	// within the ~160-char budget scrapers actually display. The book page already
	// routes its description through the same helper.
	// A bio, when this locale has one, leads (see below). When it doesn't, the localized
	// metaFallback sentence is enriched with the same era + work counts the header
	// shows (summaryBits — already localized), so a bio-less author page still offers
	// the SERP something concrete rather than a bare "free classic Christian books"
	// line. No new catalogue string; the counts matter most on translated pages,
	// where a localized bio is most often absent.
	// With a bio and books: as much of the bio as fits, then what the reader
	// can do here — "Their books are free to read on Ochorus, online or
	// offline." Search showed author pages seen often and clicked rarely; the
	// bio alone never said the books are here, free, to read. No count: it
	// would need real plurals (Arabic, Ukrainian) and young-reader editions
	// are separate rows that would inflate it.
	const readFree = $derived(
		author.books.length > 1
			? t('author.metaReadFreeBooks')
			: author.books.length === 1
				? t('author.metaReadFree')
				: ''
	);
	const description = $derived.by(() => {
		if (author.bio && readFree) {
			return `${truncateMeta(author.bio, 160 - readFree.length - 1)} ${readFree}`;
		}
		if (author.bio) return truncateMeta(author.bio);
		const base = t('author.metaFallback').replace('%name%', author.name);
		return truncateMeta(summaryBits.length ? `${base} ${summaryBits.join(' · ')}.` : base);
	});
	// The author's own card — the portrait in an arch (a monogram without one),
	// the name, dates and a line in this page's language — drawn into the build
	// for every author page, in every locale, by scripts/build-author-cards.mjs.
	// It replaced the raw portrait, which previews cropped to a strip through
	// the face.
	const ogImage = $derived(absUrl(authorCardUrl(author.slug, getLang())));

	const personLd = $derived(
		jsonLd({
			'@context': 'https://schema.org',
			'@type': 'Person',
			// The node every book and chapter by this writer names as author.
			'@id': personId(canonical),
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

	// The row's book: a reader partway through (past chapter 1 of) one of this author's books picks
	// it up here ("Continue reading" — the book page's card); anyone else gets
	// the "Start with …" suggestion in the same slot. Progress is
	// client-only, so the prerendered page and a first visit show the latter.
	let resumeBook = $state<{ book: BookSummary; order: number } | null>(null);
	$effect(() => {
		const bySlug = new Map(author.books.map((b) => [b.slug, b]));
		const rec = allProgress().find(
			// Past chapter 1, as the book page's "Continue" rule: a glance at the
			// opening chapter shouldn't replace the "Start with" suggestion.
			(r) => r.kind === 'book' && resumeOrderOf(r) > 1 && bySlug.has(r.slug) && !isFinished(r.slug)
		);
		resumeBook = rec ? { book: bySlug.get(rec.slug)!, order: resumeOrderOf(rec) } : null;
	});
	// Otherwise the first book, in the API's featured order.
	const cardBook = $derived(resumeBook?.book ?? author.books[0] ?? null);
	// The Where to start row's sermon: the first, in the API's order.
	const startSermon = $derived(author.sermons[0] ?? null);

	// The biography's opening (design #14): about three paragraphs, then
	// "Continue reading the biography", which opens the rest in place. See
	// $lib/bioFold — the rest stays in the HTML, only hidden. Opened per
	// author (client navigation between authors reuses this component, and the
	// next life should open on its own opening). A `?p=` deep link (a Notebook
	// highlight) points into the text, so it opens — on every navigation, not
	// just the first (an effect, client-only: prerender has no query string);
	// read aloud and focus mode open it too (see the markup). While folded the
	// <Reader> is `paused`: it neither restores nor saves a place in prose the
	// reader has not opened.
	const bioFold = $derived(foldBio(author.bio_html || ''));
	let bioOpenFor = $state('');
	const openBio = () => (bioOpenFor = author.slug);
	const bioFolded = $derived(bioFold.folded && bioOpenFor !== author.slug && !readerUi.focus);
	$effect(() => {
		if ($page.url.searchParams.get('p')) openBio();
	});
	// "Continue reading" unmounts itself: hand focus to the first paragraph it
	// revealed, so a keyboard or screen-reader user carries on from there
	// rather than from the top of the page.
	async function continueBio() {
		openBio();
		await tick();
		const next = bioEl?.querySelector<HTMLElement>('[data-bio-fold]');
		if (!next) return;
		next.tabIndex = -1;
		next.focus({ preventScroll: true });
	}

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
	// strings, so no new visible copy is introduced (the Q&A tab is the book page's
	// `qa.sectionTitle`, as its section heading is); it rides `showFaq`,
	// so it never appears without the section it points at (in a locale whose Q&A
	// is not yet translated the API returns none, and both drop out together).
	// In the page's order (design #14): the works, then the life, then the
	// rest. Books and Sermons carry their counts — "Books (18)".
	type NavItem = { id: string; label: string; count?: number };
	const navItems = $derived(
		[
			author.books.length ? { id: 'books', label: t('nav.books'), count: author.books.length } : null,
			author.sermons.length ? { id: 'sermons', label: t('nav.sermons'), count: author.sermons.length } : null,
			author.bio_html || author.bio ? { id: 'bio', label: t('articles.kindBiography') } : null,
			author.articles?.length ? { id: 'articles', label: t('nav.articles') } : null,
			showFaq ? { id: 'faq', label: t('qa.sectionTitle') } : null
		].filter((x): x is NavItem => x != null)
	);
	// Articles about this person: the first few, then "Show N more" (see markup).
	const ARTICLES_SHOWN = 4;
	let showAllArticles = $state(false);

	// Below two targets there is nothing to jump between.
	const showSubnav = $derived(navItems.length >= 2);

	// The bar's measured height feeds `--pinned-offset` (set on the page column),
	// the same contract the biographies index uses so anchored sections clear both
	// the app nav and this bar. Mirrors +layout's navH measurement.
	let subnavH = $state(0);
	// A cold #section load jumps against the bar's estimate; re-land it once measured.
	realignHashOnMeasure(() => subnavH);

	// Where the Reader parks a resumed or `?p=` paragraph, and the line its
	// "which paragraph is at the top" reads against: below everything pinned —
	// the app nav (this route keeps it sticky) and the jump-bar when it shows —
	// plus the same half-rem the section anchors keep. It was 0, which parked a
	// Notebook link's paragraph under the nav. Nothing is pinned in focus mode.
	const pinnedOffset = $derived(
		readerUi.focus ? 0 : readerUi.navHeight + (showSubnav ? subnavH : 0) + 8
	);

	// Scroll-spy: light the link for whatever section sits in the band just under
	// the pinned bars. The shared helper re-observes when the target set changes
	// (empty while the sub-nav is hidden). No-JS / prerender shows the bar with
	// nothing lit — the links still jump.
	const spy = scrollSpy(() => (showSubnav ? navItems.map((n) => n.id) : []));
</script>

<Seo
	title="{seoTitle} — Ochorus"
	{description}
	{canonical}
	{hreflang}
	ogType="profile"
	{ogImage}
	ogImageWidth={LANDSCAPE_WIDTH}
	ogImageHeight={LANDSCAPE_HEIGHT}
	ogImageAlt={author.photo_url ? `${t('a11y.portraitOf')} ${author.name}` : author.name}
	structuredData={[personLd, worksLd, crumbsLd, faqLd].filter((x): x is string => x != null)}
/>

<svelte:head>
	{#if thin}<meta name="robots" content="noindex" />{/if}
	<!-- Without script the "Continue reading" control cannot open the
	     biography, so it is not folded at all. -->
	<noscript
		><style>
			.bio-folded .reading > [data-bio-fold],
			.bio-folded .reading > [data-bio-fold] ~ * { display: revert !important; }
			.bio-folded .reading { -webkit-mask-image: none !important; mask-image: none !important; }
			.bio-more { display: none !important; }
		</style></noscript
	>
</svelte:head>

<!-- --pinned-offset: how far down the first pixel unobstructed by BOTH the app
     nav and this page's own sticky jump-bar is; anchored sections read it for
     scroll-margin so a jump lands below the bars. Same contract as the
     biographies index. -->
<div class="page-col px-5 py-10" style="--pinned-offset: calc(var(--appnav-h, 0px) + {subnavOffset(showSubnav, subnavH)}px)">
	<!-- Focus mode strips the page back to the life itself. Everything here is
	     context around the biography — portrait, timeline, epigraph, shelves,
	     contemporaries — and it is exactly what someone reading eleven minutes
	     of prose wants out of the way. -->
	{#if !readerUi.focus}
	<!-- On the reading column like everything below it: full-width, the trail
	     was a second left edge beside the centred page (QA, 2026-10). -->
	<div class="mx-auto w-full max-w-[40rem]">
		<Breadcrumb items={crumbs} />
	</div>

	<!-- The masthead, laid out as the book page's hero (AuthorHero): the
	     portrait on the start side; the era, the name and who they were in one
	     line beside it; then the key facts and the page's actions. -->
	<AuthorHero slug={author.slug} name={author.name} photoUrl={author.photo_url} birthYear={author.birth_year}>
		<!-- The person's name, as the book page's H1 is the book's title. The
		     "<Name> Biography, Books, and Sermons" phrase is the <title>'s. -->
		<h1 class="text-h1" dir="auto">{author.name}</h1>
		{#if identity}
			<p class="mt-2 text-body text-muted" dir="auto">{identity}</p>
		{/if}
		<!-- Their birthday, or the day they died: a candle and the date. -->
		<AuthorCandle slug={author.slug} />
		{#snippet details()}
			<!-- Key facts, only those the data holds: the years, the writer's
			     traditions and place (each a hub page of writers like them), and
			     what is here to read. -->
			<dl class="author-facts">
				{#if author.birth_year}
					<div><dt>{t('author.factBorn')}</dt><dd>{author.birth_year}</dd></div>
				{/if}
				{#if author.death_year}
					<div><dt>{t('author.factDied')}</dt><dd>{author.death_year}</dd></div>
				{/if}
				{#each hubGroups as g (g.label)}
					<div>
						<dt>{g.label}</dt>
						<dd>
							{#each g.hubs as h, i (h.slug)}{#if i > 0}{', '}{/if}<a
									href={localizeHref(hubPath(h))}
									class="text-accent hover:underline">{h.label}</a
								>{/each}
						</dd>
					</div>
				{/each}
				{#if worksBits.length || showQuotes}
					<div>
						<dt>{t('author.factHere')}</dt>
						<dd>
							<!-- The separator as an expression: literal spaces at an {#if}
							     boundary are compiler-trimmed. -->
							{#each worksBits as bit, i (i)}{#if i > 0}<span class="sep">{' · '}</span>{/if}{bit}{/each}
							<!-- The writer's quotations: a link here rather than a hero
							     button. Only with approved quotations, and only to English
							     readers: the quote page is English (lifted from the English
							     works, each citation naming an English chapter), so a locale
							     prefix would promise a page that does not exist. Un-localized
							     href for the same reason. This link also keeps the quote page
							     off the list of pages reachable only from the sitemap. -->
							{#if showQuotes}{#if worksBits.length}<span class="sep">{' · '}</span>{/if}<a
									href={`/quotes/${author.slug}/`}
									class="text-accent hover:underline"
									>{author.quote_count} {author.quote_count === 1 ? 'quote' : 'quotes'}</a
								>{/if}
						</dd>
					</div>
				{/if}
			</dl>

			<!-- The page's actions: Follow is the one outlined button; Share, and
			     Search this author's works (the real search, scoped to them), are
			     quiet icons beside it. The biography's reading tools live with the
			     biography below. -->
			<div class="author-actions mt-4 flex flex-wrap items-center gap-1">
				<FavoriteButton kind="author" slug={author.slug} showLabel />
				<ShareButton url={canonical} title={author.name} />
				<a
					href={localizeHref(scopedSearchHref('author', author.slug))}
					class="btn btn-icon btn-ghost"
					aria-label={t('search.inAuthor')}
					title={t('search.inAuthor')}><Icon name="search" size={18} /></a
				>
			</div>
		{/snippet}
	</AuthorHero>

	<!-- Where to start (design #14): ONE row with a book, a plan and a sermon —
	     only those that exist. It replaced two boxes, a "Start with" read card
	     and a plan card, that said the same thing twice. The book keeps the
	     solid read verb (the shared .read-card's job, design #2) and, for a
	     reader partway through (past chapter 1 of) one of this author's books,
	     becomes "Continue reading" with the progress. Progress is client-only,
	     so the prerendered page and a first visit show the suggestion. -->
	{#if cardBook || authorPlan || startSermon}
		<section class="start-row mx-auto mt-6 max-w-[40rem]" aria-labelledby="start-heading">
			<h2 id="start-heading" class="eyebrow text-muted">{t('hubs.startReading')}</h2>
			<div class="start-items mt-2">
				{#if cardBook}
					<div class="start-item start-book">
						<div class="flex items-start gap-3">
							<div class="w-12 shrink-0"><BookCover book={cardBook} rounded="rounded-[3px]" /></div>
							<div class="min-w-0 flex-1">
								<p class="text-small text-muted">
									{#if resumeBook}
										{t('continue.title')} · {t('book.chapterOf')
											.replace('%n%', String(resumeBook.order))
											.replace('%t%', String(cardBook.chapter_count))}
									{:else}
										{t('author.startWith')}
									{/if}
								</p>
								<p class="start-title" dir="auto">{cardBook.title}</p>
								{#if resumeBook}
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
								{/if}
							</div>
						</div>
						<a
							href={localizeHref(
								chapterPath(cardBook.slug, resumeBook ? resumeBook.order : 1, cardBook.has_modern_edition)
							)}
							class="btn btn-primary btn-solid mt-3 w-full">{resumeBook ? t('book.continue') : t('book.beginReading')}</a
						>
					</div>
				{/if}
				{#if authorPlan}
					<a class="start-item start-link" href={localizeHref(`/plans/${authorPlan.slug}`)}>
						<span class="text-small text-muted">{t('search.typePlan')}</span>
						<span class="start-title" dir="auto">{authorPlan.title}</span>
						<span class="text-small text-muted">{authorPlan.day_count} {t('plans.days')} <Arrow /></span>
					</a>
				{/if}
				{#if startSermon}
					<a class="start-item start-link" href={localizeHref(`/sermons/${startSermon.slug}`)}>
						<span class="text-small text-muted">{t('search.typeSermon')}</span>
						<span class="start-title" dir="auto">{startSermon.title}</span>
						<span class="text-small text-muted">{readingTime(startSermon.word_count)} <Arrow /></span>
					</a>
				{/if}
			</div>
		</section>
	{/if}

	<!-- On-page jump navigation: Books (N) · Sermons (N) · Biography · Articles ·
	     Q&A, in the order the sections now run. Sits under the Where to start
	     row, then pins under the app nav (`--appnav-h`) on scroll and lights the
	     section in view (scrollSpy); its measured height feeds `--pinned-offset`
	     above. Hidden in focus mode with the rest of the page context. Only shown
	     when there are ≥2 sections to move between. -->
	{#if showSubnav}
		<nav
			bind:clientHeight={subnavH}
			class="author-subnav sticky z-(--z-pinned) mt-6 bg-bg"
			style="top: var(--appnav-h, 0px)"
			aria-label={t('a11y.pageSections')}
		>
			<!-- Tabs centred when they fit, start-aligned when they don't (plain
			     `justify-center` on a scroller pushed the first tabs out of scroll
			     reach). The rule spans the reading column, not the page; the nav
			     stays full-width so its ground still covers text scrolling under. -->
			<div class="mx-auto w-full max-w-[40rem] border-b border-border">
				<ul class="tab-strip flex justify-center-safe gap-1" use:tabStrip={spy.active}>
					{#each navItems as item (item.id)}
						<li>
							<a
								href="#{item.id}"
								class="subnav-link"
								class:is-active={spy.active === item.id}
								aria-current={spy.active === item.id ? 'true' : undefined}
								onclick={(e) => spy.jump(e, item.id)}
								>{item.label}{#if item.count}<span class="subnav-count">{' '}({item.count})</span>{/if}</a
							>
						</li>
					{/each}
				</ul>
			</div>
		</nav>
	{/if}

	<!-- The works come first (design #14): most visitors came for the books,
	     which used to start some 1,500 words of biography down. -->
	{#if author.books.length}
		<section id="books" class="jump-anchor mx-auto mt-8 max-w-[40rem]">
			<h2 class="section-heading">
				{t('author.booksBy')} {author.name}
				<span class="text-small font-normal count">({author.books.length})</span>
			</h2>
			<!-- Three across at most: the page is one reading-width column, so a
			     writer's shelf sits as a handful of real covers, not a thumbnail grid. -->
			<div class="grid grid-cols-2 gap-5 sm:grid-cols-3">
				{#each author.books as book (book.slug)}
					<BookCard {book} />
				{/each}
			</div>
		</section>
	{/if}

	<!-- Sermons as compact rows — the shared SermonCard row, one per line, so a
	     preacher's sermons read as a list under the shelf rather than a second
	     grid of boxes. -->
	{#if author.sermons.length}
		<section
			id="sermons"
			class="jump-anchor deferred mx-auto mt-12 max-w-[40rem]"
			style="contain-intrinsic-block-size: auto {4 + author.sermons.length * 6.5}rem"
		>
			<h2 class="section-heading">
				{t('author.sermonsBy')} {author.name}
				<span class="text-small font-normal count">({author.sermons.length})</span>
			</h2>
			<!-- The shared row, not a hand-rolled list: this one used to compute
			     its own length with Math.round(word_count / 200), which could
			     disagree with the figure on the sermon's own page. -->
			<div class="sermon-list">
				{#each author.sermons as sermon (sermon.slug)}
					<SermonCard {sermon} />
				{/each}
			</div>
		</section>
	{/if}

	<!-- Books about them: a work whose lone subject they are (a Portraits of
	     Courage life, a Key Teachings companion). They did not write it — its
	     author is Ochorus Originals, which showAuthor says — but it is the next
	     thing a reader of their page wants, so it follows their own work rather
	     than waiting among the anthologies below. -->
	{#if booksAbout.length}
		<section id="about-them" class="jump-anchor deferred mx-auto mt-12 max-w-[40rem]">
			<h2 class="section-heading">
				{t('author.booksAbout')} {author.name}
				<span class="text-small font-normal count">({booksAbout.length})</span>
			</h2>
			<div class="grid grid-cols-2 gap-5 sm:grid-cols-3">
				{#each booksAbout as book (book.slug)}
					<BookCard {book} showAuthor />
				{/each}
			</div>
		</section>
	{/if}

	<!-- Also appears in: books this person is FOUND IN but did not write
	     (BookPerson) — an anthology that features them. Book cards, not person
	     cards, and showAuthor so it's clear whose work it is. -->
	{#if appearsIn.length}
		<section class="deferred mx-auto mt-12 max-w-[40rem]">
			<h2 class="section-heading">{t('author.appearsIn')}</h2>
			<div class="grid grid-cols-2 gap-5 sm:grid-cols-3">
				{#each appearsIn as book (book.slug)}
					<BookCard {book} showAuthor />
				{/each}
			</div>
		</section>
	{/if}
	{/if}

	<!-- The biography, after the works. One section, so the jump-bar's
	     Biography tab stays lit while the prose is on screen. -->
	{#if author.bio_html || author.bio}
	<section id="bio" class="jump-anchor" class:mt-12={!readerUi.focus}>
		{#if !readerUi.focus}
		<!-- The biography's heading carries its own reading tools — Listen, text
		     settings, focus mode apply to the life story, not to the page, so they
		     sit with it rather than among the page actions above. -->
		<div class="bio-head mx-auto flex max-w-[40rem] items-center gap-3">
			<h2 class="font-display text-h2 font-semibold">{t('articles.kindBiography')}</h2>
			{#if author.bio_html}
				<div class="reader-tools ms-auto shrink-0">
					{#if listen.offered}
						<button
							class="btn btn-icon btn-ghost"
							class:text-accent={listen.status !== 'idle'}
							onclick={() => {
								if (listen.status !== 'idle') return listen.stop();
								// Read aloud runs through the whole life: open it first.
								openBio();
								reader?.startListening();
							}}
							aria-label={t('reader.listen')}
							title={t('reader.listen')}><Icon name="headphones" size={16} /></button
						>
					{/if}
					<ReaderControls />
					<button
						class="btn btn-icon btn-ghost"
						onclick={() => {
							// Focus mode is for reading the whole life; leaving it
							// should not fold the text back up under the reader.
							openBio();
							readerUi.toggleFocus();
						}}
						aria-label={t('reader.focus')}
						title={t('reader.focus')}><Icon name="maximize" size={18} /></button
					>
				</div>
			{/if}
		</div>

		<!-- Lifespan timeline: their own milestones when curated, else the bare
		     lifespan bar (see LifeTimeline). -->
		<LifeTimeline
			birthYear={author.birth_year}
			deathYear={author.death_year}
			milestones={author.milestones}
			labels={getLang() === 'en'}
		/>
		{/if}

		<!-- Biography. The band — not the page — carries the reader's CSS variables,
		     so the width/size/typeface controls govern the prose while the portrait,
		     book grid and contemporaries keep the page's own layout. `bioLabels`
		     rides along on the same element: custom properties inherit, so the
		     prayer-callout ::before labels reach the injected HTML.

		     The opening only, until the reader asks for the rest (design #14):
		     `bioFold` marks where the opening ends and `.bio-folded` hides the
		     rest with CSS. It stays in the DOM, so the prerendered page carries
		     the whole life for search, and the Reader's paragraph indices
		     (resume, highlights, `?p=`, read aloud) are those of the full text.
		     Focus mode always shows all of it. The pull quote the header used to
		     lift out of the bio is gone: it is the bio's own blockquote, shown
		     once, in place. -->
		{#if author.bio_html}
			<div
				id="bio-text"
				class="mx-auto mt-8"
				class:bio-folded={bioFolded}
				style="{readerPrefs.style}; {bioLabels}; max-width: var(--reading-measure)"
			>
				<Reader
					bind:this={reader}
					kind="bio"
					slug={author.slug}
					order={BIO_CHAPTER_ORDER}
					language={data.language as string}
					html={bioFold.html}
					class="bio"
					{cite}
					listenTitle={author.name}
					listenArtist={t('bios.eyebrow')}
					bind:body={bioEl}
					bind:frac
					headerOffset={pinnedOffset}
					paused={bioFolded}
				/>
				{#if bioFolded}
					<!-- Present only while folded, so `aria-expanded` is always false;
					     once opened the control is gone and focus moves into the
					     revealed text (continueBio). -->
					<button
						type="button"
						class="bio-more"
						aria-controls="bio-text"
						aria-expanded="false"
						onclick={continueBio}
					>
						{t('author.continueBio')} · {readingTime(bioWords)} <Arrow />
					</button>
				{/if}
			</div>
		{:else}
			<p class="mx-auto mt-6 max-w-[40rem] text-body leading-relaxed text-muted">{smartQuotes(author.bio, data.language as string)}</p>
		{/if}
	</section>
	{/if}

	{#if !readerUi.focus}
	<!-- After the biography, so a writer with a life but no works yet does not
	     open on a dead end. -->
	{#if !author.books.length && !author.sermons.length && !author.appears_in?.length}
		<div class="mt-10"><EmptyState message={t('author.empty')} /></div>
	{/if}

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

	<!-- Articles that name this person (the API's `articles` /
	     articles_for_author, which documents the rule). The mirror of the book
	     page's Reader's guide: an article reachable only from the /articles hub
	     sits too deep in the link graph to earn a crawl, and an author page is
	     crawled far more often. Per-language — an untranslated locale gets an
	     empty list and no section at all. Below the works, because these are
	     writing ABOUT this person, not BY them. -->
	{#if author.articles?.length}
		<section id="articles" class="jump-anchor deferred mx-auto mt-12 max-w-[40rem]">
			<h2 class="section-heading">
				{t('author.articlesAbout')}
				{author.name}
				<span class="text-small font-normal count">({author.articles.length})</span>
			</h2>
			<!-- The first few, then "Show N more" (as on a topic page): 22 cards ran
			     nine phone screens. The rest stay in the HTML (display:none) so the
			     prerendered page still links every article. -->
			<ul id="author-articles" class="mt-3 flex flex-col gap-3">
				{#each author.articles as article, i (article.slug)}
					<li class:hidden={!showAllArticles && i >= ARTICLES_SHOWN}>
						<ArticleLinkCard {article} cta={t('author.readArticle')} />
					</li>
				{/each}
			</ul>
			{#if author.articles.length > ARTICLES_SHOWN}
				<button
					type="button"
					class="btn btn-sm btn-ghost mt-3"
					aria-controls="author-articles"
					aria-expanded={showAllArticles}
					onclick={() => (showAllArticles = !showAllArticles)}
				>
					{showAllArticles
						? t('search.showLess')
						: t('bios.showMore').replace('%n%', String(author.articles.length - ARTICLES_SHOWN))}
				</button>
			{/if}
		</section>
	{/if}

	<!-- More lives to explore: nearest contemporaries by era. -->
	{#if contemporaries.length}
		<section class="deferred mx-auto mt-12 max-w-[40rem] border-t border-border pt-8">
			<h2 class="section-heading">{t('author.moreLives')}</h2>
			<div class="grid grid-cols-2 gap-4 sm:grid-cols-3">
				{#each contemporaries as c (c.slug)}
					<PersonCard person={c} />
				{/each}
			</div>
		</section>
	{/if}

	<!-- Questions and answers — the editorial set for this author (see `faq`
	     in the script), the page's last section, every answer closed until asked
	     (design #14). Renders only with two or more entries. The visible
	     accordion and the FAQPage JSON-LD are built from one array, so they cannot
	     disagree; a closed <details> still carries its answer in the HTML. -->
	{#if showFaq}
		<section id="faq" class="jump-anchor deferred mx-auto mt-12 max-w-[40rem]">
			<!-- Localized: the API serves the Q&A per locale (AuthorTranslation.faq),
			     so the heading follows the reader's language too. Reuses the same
			     `qa.sectionTitle` key the book Q&A section uses, so the two read
			     identically. -->
			<h2 class="section-heading">{t('qa.sectionTitle')}</h2>
			<div class="faq-list">
				{#each faq as item, i (i)}
					<details class="faq-item">
						<summary>{item.q}</summary>
						<p class="faq-a">{item.a}</p>
					</details>
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
{#if !readerUi.focus && !bioFolded && listen.status === 'idle' && frac > 0.01 && frac < 0.99}
	<div class="min-left" aria-hidden="true">{minutesLeft} {t('sermon.minLeft')}</div>
{/if}

<!-- Bookmark the spot: floats, because this page's header scrolls away. -->
{#if author.bio_html}<FloatingBookmark {bookmark} {frac} />{/if}

<style>
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

	/* The shelves away from the top of the page (sermons, books about them,
	   articles, Q&A, more lives — not the books, which open the page now)
	   skip style, layout and paint until they near the viewport: a
	   prolific writer's page runs to hundreds of cards, and every state change
	   on it (a tap that opens a brief, the sub-nav lighting a tab) otherwise
	   recalcs all of them (INP). `auto` remembers each section's real height
	   once it has rendered; the figure is only a first guess. Jumps still land:
	   the jump-bar's targets were checked in Chromium, smooth and cold `#id`,
	   with guesses a third of the real height. None holds anything sticky.
	   Paint containment would clip the cards' hover shadows at the section's
	   edges, so the clip edge is pushed out — and where the browser can't do
	   that (overflow-clip-margin), the sections simply render as before. */
	@supports (overflow-clip-margin: 1px) {
		.deferred {
			content-visibility: auto;
			contain-intrinsic-block-size: auto 30rem;
			overflow-clip-margin: 2rem;
		}
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

	/* Long-form biography styling. Targets the injected {@html} via :global.
	   Pull-quotes and prayer callouts stand out.

	   Type is NOT set here any more: the element is `.reading.bio`, so size,
	   leading, typeface and colour come from the reader's CSS variables and the
	   text-settings control moves them. Re-declaring them here would silently
	   win over the reader on this one surface. */
	:global(.bio p) {
		margin: 0 0 1.15em;
	}
	/* The life opens with the site's one initial — app.css's drop-cap rule
	   includes `.reading.bio` — so its face, colour, gilt and script gate
	   (none for Arabic or Hindi) are a chapter's. */
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
	/* The hero's key facts: a quiet two-column list, muted labels in one
	   column and their values in the next, as a biography's fact box. */
	.author-facts {
		display: grid;
		grid-template-columns: auto minmax(0, 1fr);
		gap: 0.3rem 1rem;
		margin: 1rem 0 0;
		font-size: var(--fs-small);
	}
	.author-facts > div {
		display: contents;
	}
	.author-facts dt {
		color: var(--muted);
	}
	.author-facts dd {
		margin: 0;
		color: var(--text);
	}
	/* Follow keeps its outline; Share and Search beside it are bare icons. */
	.author-actions :global(.btn-icon) {
		border-color: transparent;
	}
	/* Where to start (design #14): one band, the book first and widest, then
	   the plan and the sermon, divided by hairlines. Side by side when the
	   column has room for them, stacked on a phone. */
	.start-row {
		container: start-row / inline-size;
	}
	.start-items {
		display: flex;
		flex-direction: column;
		border-radius: var(--radius-card);
		background: var(--surface-2);
	}
	.start-item {
		display: flex;
		flex-direction: column;
		gap: 0.15rem;
		min-width: 0;
		padding: 0.85rem 1rem;
	}
	.start-item + .start-item {
		border-block-start: 1px solid var(--border);
	}
	@container start-row (min-width: 34rem) {
		.start-items {
			flex-direction: row;
		}
		.start-item {
			flex: 1 1 0;
		}
		.start-book {
			flex-grow: 1.6;
		}
		.start-item + .start-item {
			border-block-start: 0;
			border-inline-start: 1px solid var(--border);
		}
	}
	.start-title {
		margin-top: 0.15rem;
		font-family: var(--font-display);
		font-size: var(--fs-h3);
		line-height: 1.25;
		color: var(--text);
	}
	.start-link {
		text-decoration: none;
	}
	.start-link:hover .start-title {
		color: var(--accent);
	}
	.start-link :global(.arrow) {
		color: var(--accent);
	}

	/* The jump-bar's counts: quieter than the label they qualify. */
	.subnav-count {
		color: var(--muted);
		font-weight: 400;
	}

	/* The biography's opening (design #14). Everything from the fold mark on
	   is hidden, not removed — the prerendered HTML keeps the whole life. The
	   opening fades out into the "Continue reading" control. */
	.bio-folded :global(.reading > [data-bio-fold]),
	.bio-folded :global(.reading > [data-bio-fold] ~ *) {
		display: none;
	}
	.bio-folded :global(.reading) {
		-webkit-mask-image: linear-gradient(to bottom, black calc(100% - 5rem), transparent);
		mask-image: linear-gradient(to bottom, black calc(100% - 5rem), transparent);
	}
	.bio-more {
		display: inline-flex;
		align-items: center;
		gap: 0.35rem;
		margin-top: 0.25rem;
		padding-block: 0.5rem;
		font-family: var(--font-sans);
		font-size: var(--fs-body);
		font-weight: 600;
		color: var(--accent);
	}
	.bio-more:hover {
		text-decoration: underline;
	}
</style>
