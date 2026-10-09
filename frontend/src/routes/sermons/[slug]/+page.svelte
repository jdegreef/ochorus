<script lang="ts">
	import { define } from '$lib/define.svelte';
	import { mediaFlag } from '$lib/mediaFlag.svelte';
	import { PHONE } from '$lib/breakpoints';
	import Arrow from '$lib/components/Arrow.svelte';
	import { readerBookmark } from '$lib/readerBookmark.svelte';
	import { hydrateSrc } from '$lib/hydrateSrc';
	import { onMount, type Component } from 'svelte';
	import { type Sermon, type SermonSummary, listSermons } from '$lib/library-public';
	import { readerPrefs } from '$lib/readerPrefs.svelte';
	import { readerUi } from '$lib/readerUi.svelte';
	import { nextBarHidden } from '$lib/readerAutohide';
	import FocusExit from '$lib/components/FocusExit.svelte';
	import LanguageFallbackNotice from '$lib/components/LanguageFallbackNotice.svelte';
	import { editionSeo, languageFallback } from '$lib/languageFallback';
	import { i18n } from '$lib/i18n.svelte';
	import {
		contentLang,
		readingTime,
		minutesLeft as minutesLeftOf,
		preachedYear,
		HEADER_OFFSET
	} from '$lib/reading';
	import { getLang } from '$lib/lang.svelte';
	import { hasLocalizedSermonCard } from '$lib/sermonOgLocales';
	import { listen } from '$lib/listen.svelte';
	import { scripture, type ScriptureResult } from '$lib/scripture.svelte';
	import { apiFetch } from '$lib/api';
	import { page } from '$app/stores';
	import { buildOutline, type OutlineEntry } from '$lib/sermonOutline';
	import { scrollSpy, jumpToSection } from '$lib/scrollSpy.svelte';
	import { absUrl, jsonLd, breadcrumbLd, truncateMeta, stripHtml, faqPage, toQa, REVIEWED_UI_LOCALES, publisherLd, personId } from '$lib/seo';
	import { focusTrap } from '$lib/actions/focusTrap';
	import { dismissable } from '$lib/actions/dismissable';
	import { hasNativeShare, nativeShare, shareLinks } from '$lib/share';
	import { favorites } from '$lib/favorites.svelte';
	import { localizeHref } from '$lib/href';
	import { authorLdType, authorPath } from '$lib/originals';
	import Breadcrumb from '$lib/components/Breadcrumb.svelte';
	import { portraitPosition } from '$lib/portraits';
	import Reader from '$lib/components/Reader.svelte';
	import ReaderControls from '$lib/components/ReaderControls.svelte';
	import Seo from '$lib/components/Seo.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import SermonPlate from '$lib/components/SermonPlate.svelte';
	import FootFeedback from '$lib/components/FootFeedback.svelte';

	let { data } = $props();
	const sermon = $derived(data.sermon as Sermon);
	const t = i18n.t;

	/**
	 * Escape leaves focus (immersive) mode. readerUi.exitFocus() existed and
	 * nothing on this page called it, so the only way out was finding the
	 * floating "Exit focus" pill. The outline drawer runs its own focus trap
	 * with an onEscape, so it keeps handling its own key.
	 */
	function onKeydown(e: KeyboardEvent) {
		if (e.key !== 'Escape' || e.metaKey || e.ctrlKey || e.altKey) return;
		// An open popover closes on its own Escape; leaving focus mode on the
		// same press lost both at once.
		if (outlineOpen || define.open || scripture.open || !readerUi.focus) return;
		e.preventDefault();
		readerUi.exitFocus();
	}

	// The reader owns the prose and everything that reads it; this page owns its
	// own chrome. `body` comes back out for the outline, `frac` for the progress
	// bar, and the instance for the Listen button.
	let reader = $state<Reader | undefined>();
	let body = $state<HTMLElement | undefined>();
	let frac = $state(0);
	const minsLeft = $derived(minutesLeftOf(sermon.word_count, frac));

	// --- Bookmarks ------------------------------------------------------------
	// The paragraph at the top of the screen — the single-document Reader's
	// bookmark, shared with the biography and article pages.
	const bookmark = readerBookmark({
		kind: 'sermon',
		slug: () => sermon.slug,
		title: () => sermon.title,
		reader: () => reader,
		body: () => body,
		frac: () => frac
	});

	// Other sermons on the same Bible book, fetched client-side (page is
	// prerendered; the list is small and cached by the browser).
	let related = $state<SermonSummary[]>([]);

	// --- Jump-to-section outline ----------------------------------------------
	// Built from the rendered body once it's in the page (headings + the classic
	// "I. / II. / III." homiletic points). Shown only when there's real structure
	// to navigate.
	let outline = $state<OutlineEntry[]>([]);
	let outlineOpen = $state(false);
	// Where the popover hangs: measured from the toggle that opened it, so it
	// drops just under that button instead of a guessed offset that sat over the
	// global nav and missed a bar that tracks --reading-measure.
	let outlinePos = $state('');

	function toggleOutline(e: MouseEvent) {
		if (outlineOpen) {
			outlineOpen = false;
			return;
		}
		const r = (e.currentTarget as HTMLElement).getBoundingClientRect();
		const vw = document.documentElement.clientWidth;
		const rtl = getComputedStyle(document.documentElement).direction === 'rtl';
		// inset-inline-end: the gap from the viewport's end edge to the button's.
		const end = Math.max(12, rtl ? r.left : vw - r.right);
		// …and never wider than the room left before the start edge, or on a
		// phone (toggle well in from the end) it ran off the screen.
		outlinePos =
			`top: ${Math.round(r.bottom + 6)}px; inset-inline-end: ${Math.round(end)}px; ` +
			`max-width: ${Math.round(vw - end - 12)}px`;
		outlineOpen = true;
	}

	// The top bar's "⋯" group (save, share, focus — plus bookmark on phones) —
	// the chapter reader's pattern, so the two bars read the same.
	let moreOpen = $state(false);
	/** Close the "⋯" group, then run the chosen action. */
	const fromMore = (action: () => void) => () => {
		moreOpen = false;
		action();
	};
	const saved = $derived(favorites.has('sermon', sermon.slug));
	const shareLabel = $derived(`${sermon.title} — ${sermon.author_name}`);
	// Share from the "⋯" group ($lib/share, as ShareButton): the OS sheet
	// where there is one. Where there isn't — or it fails for any reason but
	// a dismissal — the row becomes Copy link and the fallback targets appear
	// under it, with the menu left open to pick from.
	let showTargets = $state(false);
	let copied = $state(false);
	let copyTimer: ReturnType<typeof setTimeout> | undefined;
	$effect(() => () => clearTimeout(copyTimer));
	async function shareFromMore() {
		if (!showTargets) {
			const r = await nativeShare(shareLabel, canonical);
			if (r !== 'unavailable') {
				moreOpen = false;
				return;
			}
			showTargets = true;
			return;
		}
		try {
			await navigator.clipboard.writeText(canonical);
			copied = true;
			clearTimeout(copyTimer);
			copyTimer = setTimeout(() => (copied = false), 1500);
		} catch {
			// Clipboard blocked: the address bar still holds the link.
		}
	}

	// Phones get the chapter reader's footer row (Listen · + · Aa) instead of
	// Listen and Aa in the top bar. Only one <ReaderControls> mounts — the
	// popover and the phone sheet share readerUi.panelOpen.
	// mediaFlag, not svelte/reactivity's MediaQuery: hydration-safe (false in
	// the prerendered markup), so both `{#if}`s below agree with it.
	const phone = mediaFlag(PHONE);
	const isPhone = $derived(phone.matches);

	// The footer's action row folds away while reading on and returns on the
	// first scroll up, as the chapter's does (nextBarHidden). Folding changes no
	// LAYOUT: the spacer and --foot-h keep the unfolded height, or shrinking them
	// at the sermon's end would clamp scrollY upward, read as a scroll-up, and
	// unfold it again — the chapter's flicker loop (page-design skill).
	let footFolded = $state(false);
	$effect(() => {
		if (!isPhone) return;
		let last = window.scrollY;
		const onScroll = () => {
			const y = window.scrollY;
			footFolded = nextBarHidden(footFolded, y, last, window.innerHeight);
			last = y;
		};
		window.addEventListener('scroll', onScroll, { passive: true });
		return () => window.removeEventListener('scroll', onScroll);
	});
	// Never folded while something the row opened (the Aa sheet) owns the screen.
	const foldActions = $derived(footFolded && !readerUi.panelOpen);

	// The footer's unfolded height, published as --foot-h for the spacer below
	// and for fixed UI that clears it (the selection bar). Removed with the footer.
	let footEl = $state<HTMLElement>();
	$effect(() => {
		const el = footEl;
		if (!el) return;
		const root = document.documentElement;
		const ro = new ResizeObserver(() => {
			if (el.querySelector('.foot-actions.folded')) return;
			root.style.setProperty('--foot-h', `${el.offsetHeight}px`);
		});
		ro.observe(el);
		return () => {
			ro.disconnect();
			root.style.removeProperty('--foot-h');
		};
	});

	/** Scroll to a fraction of the sermon — drives the footer's scrubber. */
	function scrubTo(to: number) {
		if (!body) return;
		const rect = body.getBoundingClientRect();
		const top = window.scrollY + rect.top;
		window.scrollTo({ top: Math.max(0, top - window.innerHeight + to * rect.height) });
	}
	$effect(() => {
		void sermon.slug; // rebuild when navigating between sermons
		outline = body ? buildOutline(body) : [];
	});
	// Which section the reader is in — for the desktop rail's highlight. The
	// shared scroll-spy re-observes as the outline is (re)built; `--pinned-offset`
	// on the article (below) keeps its jumps landing below the reader bar.
	const spy = scrollSpy(() => outline.map((s) => s.id));

	// Jump to an outline section and close the popover. The landing offset lives
	// in CSS (`.sec-anchor` scroll-margin, below), not scrollTo math.
	function scrollToSection(id: string) {
		jumpToSection(id);
		outlineOpen = false;
	}

	const initials = (name: string) =>
		name
			.split(' ')
			.filter(Boolean)
			.map((w) => w[0])
			.slice(0, 2)
			.join('')
			.toUpperCase();

	// The sermon's preaching text — the verse(s) it's built on — for the header
	// card. Fetched client-side (the page is prerendered); absent = card shows
	// just the reference.
	let preachingText = $state<ScriptureResult | null>(null);
	$effect(() => {
		const ref = sermon.scripture_ref;
		preachingText = null;
		if (!ref) return;
		apiFetch<ScriptureResult>(`/api/library/scripture/?ref=${encodeURIComponent(ref)}`)
			.then((v) => (preachingText = v))
			.catch(() => (preachingText = null));
	});

	/** "1 Peter 2:7" -> "1 Peter"; "Matthew 11:28" -> "Matthew". */
	const refBook = (ref: string) => ref.match(/^(\d?\s?[A-Za-z]+)/)?.[1]?.trim() ?? '';
	const book = $derived(refBook(sermon.scripture_ref || ''));

	// onMount, not $effect: `listSermons` fetches the whole catalogue with no
	// memo, and an effect keyed on `book` would re-issue it on every
	// sermon→sermon navigation just to fill a footer list. (That also means the
	// list doesn't refresh on client-side nav — pre-existing, and a fair thing to
	// fix once `listSermons` is memoised.)
	onMount(() => {
		readerPrefs.init();
		// Related sermons, ranked by shared topic first (the topic tags give
		// relevance a scripture-only match missed), then a shared Bible book — and
		// a sermon with no passage of its own still gets neighbours. Fetched
		// client-side (the page is prerendered; the list is small and browser-cached).
		listSermons(getLang())
			.then((all) => {
				const mine = new Set((sermon.topics ?? []).map((t) => t.slug));
				const scored = all
					.filter((s) => s.slug !== sermon.slug)
					.map((s) => {
						const shared = (s.topics ?? []).filter((t) => mine.has(t.slug)).length;
						const sameBook = book && refBook(s.scripture_ref || '') === book ? 1 : 0;
						return { s, score: shared * 2 + sameBook };
					})
					.filter((x) => x.score > 0)
					.sort((a, b) => b.score - a.score);
				// Capped: an unbounded related list is what the style guide forbids
				// (a card/section must bound its members). Six is enough to browse.
				related = scored.slice(0, 6).map((x) => x.s);
			})
			.catch(() => (related = []));
	});

	// Self-referential canonical + hreflang — an English canonical here would
	// deindex the translated sermon pages. Sermons are per-language rows with no
	// English fallback, so hreflang lists only the locales this sermon exists in.
	const path = $derived(`/sermons/${sermon.slug}/`);
	// A missing edition renders the English one (see languageFallback).
	const fallback = $derived(languageFallback(getLang(), sermon.language));
	const seo = $derived(editionSeo(path, sermon.available_languages, fallback));
	const hreflang = $derived(seo.hreflang);
	const canonical = $derived(seo.canonical);

	onMount(() => (showTargets = !hasNativeShare()));
	const shareTargets = $derived(shareLinks(shareLabel, canonical, t('login.email')));

	const year = $derived(preachedYear(sermon.preached_on));

	// --- SEO -------------------------------------------------------------------
	// Description, then structured data (an Article for the sermon plus a
	// breadcrumb). Prefer the written "In brief" summary: it reads as a snippet,
	// where the opening prose of these sermons is usually the scripture epigraph
	// itself ("I am the Lord…") — a Bible quote, not a description of the sermon.
	// Fall back to the opening prose, then the generic template. truncateMeta
	// gives a clean sentence-boundary cut (mirrors the book page).
	const metaDescription = $derived(
		truncateMeta(sermon.summary) ||
			truncateMeta(stripHtml(sermon.body_html)) ||
			t('sermon.metaFallback')
				.replace('%title%', sermon.title)
				.replace('%name%', sermon.author_name)
	);
	// The sermon's own share card — its emblem, passage and title on the house
	// ground (frontend/scripts/generate-sermon-og.mjs). This used to be the
	// AUTHOR PORTRAIT, so every Spurgeon sermon forwarded into a chat as the
	// same photograph of Spurgeon, and a sermon by an author with no portrait
	// forwarded as a bare link. Locales in SERMON_OG_LOCALES draw their own card
	// (French title, French passage); every other language shares the English
	// one. A prerendered page cannot test for a file, so the card's existence is
	// guaranteed by `SermonShareCardTests` instead, per language.
	const ogImage = $derived(
		absUrl(
			hasLocalizedSermonCard(sermon.language)
				? `/og/sermons/${sermon.language}/${sermon.slug}.png`
				: `/og/sermons/${sermon.slug}.png`
		)
	);
	// Scripture reference in the <title>/og:title: a large share of sermon
	// searches are passage-driven ("sermon on Matthew 11:28"), and the reference
	// lived only in the page body — never the title tag search engines weight
	// most. The visible H1 stays the plain title (the passage sits in the
	// text-card right below it, and the book page's H1 is the bare title too).
	const titleParts = $derived(
		[sermon.title, sermon.scripture_ref || null, sermon.author_name].filter(Boolean)
	);
	const shareTitle = $derived(titleParts.join(' — '));
	// Every passage the sermon engages, for the JSON-LD `about` (was just the
	// single preaching text). `scripture_refs` already leads with `scripture_ref`
	// when set — same field the visible scripture index reads.
	const aboutRefs = $derived(sermon.scripture_refs ?? []);
	// Topical + scriptural keywords for the Article node.
	const keywords = $derived([
		...new Set([...(sermon.topics ?? []).map((tp) => tp.title), ...aboutRefs])
	]);
	const sermonLd = $derived(
		jsonLd({
			'@context': 'https://schema.org',
			'@type': 'Article',
			headline: sermon.title,
			// The page's own snippet — the same text as its meta description.
			description: metaDescription,
			// The preacher as the node their author page declares: that page's
			// URL in THIS language (it was always the English one), its @id, and
			// the identifiers that say which person this is.
			author: {
				'@type': authorLdType(sermon.author_slug),
				'@id': personId(absUrl(localizeHref(authorPath(sermon.author_slug)))),
				name: sermon.author_name,
				url: absUrl(localizeHref(authorPath(sermon.author_slug))),
				sameAs: sermon.author_same_as?.length ? sermon.author_same_as : undefined
			},
			inLanguage: sermon.language,
			url: canonical,
			mainEntityOfPage: { '@type': 'WebPage', '@id': canonical },
			isAccessibleForFree: true,
			datePublished: sermon.preached_on || undefined,
			dateModified: sermon.updated_at || undefined,
			wordCount: sermon.word_count || undefined,
			image: ogImage,
			about: aboutRefs.length ? aboutRefs.map((ref) => ({ '@type': 'Thing', name: ref })) : undefined,
			keywords: keywords.length ? keywords : undefined,
			publisher: publisherLd()
		})
	);
	// One trail feeds both the visible <Breadcrumb> and the JSON-LD (they had
	// drifted: the visible nav went Sermons › Author, the JSON-LD Home › Sermons
	// › Title). Home › Sermons › Title, the book page's shape.
	const crumbs = $derived([
		{ name: t('common.home'), href: '/' },
		{ name: t('nav.sermons'), href: '/sermons' },
		{ name: sermon.title, href: `/sermons/${sermon.slug}` }
	]);
	const crumbsLd = $derived(breadcrumbLd(crumbs));

	// Answered study questions — a "Questions for reflection" section and the
	// matching FAQPage JSON-LD, both from the one `study_questions` array so the
	// markup can never assert a question the page doesn't show. The question/answer
	// TEXT is per-sermon content (already in the sermon's language); only the
	// section HEADING is catalogue copy, so — like the book page's FAQ — the
	// section is gated to locales whose heading is native-reviewed. English-only
	// content today, so in practice this renders for en. (Google restricted FAQ
	// rich results to authoritative sites in 2023; the value here is the unique
	// content and the clean entity signal, not a SERP accordion.)
	const faqItems = $derived(
		REVIEWED_UI_LOCALES.has(getLang())
			? toQa(sermon.study_questions)
			: []
	);
	const faqLd = $derived(faqItems.length ? faqPage(faqItems) : '');

	// Each study question can be answered into the reader's Notebook. The box
	// loads on the client once the page is up — the questions themselves are
	// prerendered for search, and the journal store is for the reader alone.
	let ReflectBox = $state<Component<Record<string, unknown>> | null>(null);
	onMount(() => {
		if (!faqItems.length) return;
		import('$lib/components/notebook/ReflectBox.svelte').then(
			(mod) => (ReflectBox = mod.default as unknown as Component<Record<string, unknown>>)
		);
	});

	// Selecting text offers copy-quote / share (with attribution), highlight and
	// note; a single word opens the dictionary — same as the chapter reader.
	const cite = $derived({
		author: sermon.author_name,
		book: sermon.title,
		chapter: '',
		url: $page.url.href
	});
</script>

<Seo
	title="{shareTitle} — Ochorus"
	description={metaDescription}
	{canonical}
	{hreflang}
	ogType="article"
	ogTitle={shareTitle}
	{ogImage}
	structuredData={[sermonLd, crumbsLd, faqLd].filter(Boolean)}
/>

<svelte:window onkeydown={onKeydown} />

<!-- Scroll-progress bar, pinned to the very top of the viewport. -->
<div class="read-progress" style="transform: scaleX({frac})" aria-hidden="true"></div>

<!-- Reader top bar -->
{#if !readerUi.focus}
	<div class="reader-chrome sticky top-0 z-(--z-pinned) border-b border-border bg-bg/90 backdrop-blur">
		<!-- Tracks the article below it (same `--reading-measure`, same `px-5`)
		     rather than sitting at a flat 48rem, which was wider than the text at
		     small settings and far narrower at large ones. The floor keeps the
		     controls from crushing at narrow/0.8x; the min() keeps that floor
		     inside a phone. -->
		<div
			class="mx-auto flex items-center justify-between gap-0.5 px-5 py-1.5 sm:gap-3 sm:py-2.5"
			style="max-width: min(max(var(--reading-measure), 32rem), 100%)"
		>
			<!-- Phone bar: Back · which sermon · Outline · "⋯" (the shared one at
			     the end of the row) — the chapter reader's phone bar. Listen and Aa
			     live in the footer row; Bookmark, Save, Share and Focus fold into "⋯". -->
			<div class="flex min-w-0 flex-1 items-center gap-0.5 sm:hidden">
				<a
					href={localizeHref('/sermons')}
					class="btn btn-icon btn-ghost min-w-11 shrink-0"
					aria-label={t('nav.sermons')}
					title={t('nav.sermons')}><Icon name="chevron-left" size={20} /></a
				>
				<div class="min-w-0 flex-1 text-center">
					<div
						class="truncate text-small font-semibold text-text"
						dir="auto"
						lang={contentLang(sermon.language)}
					>
						{sermon.title}
					</div>
					<div class="truncate text-small text-muted"><bdi>{sermon.author_name}</bdi></div>
				</div>
				{#if outline.length >= 2}
					<button
						class="btn btn-icon btn-ghost min-w-11 shrink-0"
						class:text-accent={outlineOpen}
						onclick={toggleOutline}
						aria-label={t('sermon.outline')}
						title={t('sermon.outline')}
						aria-expanded={outlineOpen}><Icon name="list" size={20} /></button
					>
				{/if}
			</div>
			<a
				href={localizeHref('/sermons')}
				class="hidden min-w-0 truncate text-small text-muted hover:text-text sm:block"
				><Arrow back /> {t('nav.sermons')}</a
			>
			<!-- From `sm`, the chapter bar's shape: Outline (where Contents stands) ·
			     Bookmark · Listen · Aa · "⋯", labelled from `md`; Save, Share and
			     Focus fold into "⋯". -->
			<div class="flex shrink-0 items-center gap-0.5">
				<div class="hidden sm:contents">
					{#if outline.length >= 2}
						<button
							class="outline-toggle-btn btn btn-icon btn-ghost"
							class:text-accent={outlineOpen}
							onclick={toggleOutline}
							aria-label={t('sermon.outline')}
							title={t('sermon.outline')}
							aria-expanded={outlineOpen}><Icon name="list" size={18} /></button
						>
					{/if}
					<!-- Labelled from `md`; the aria-label matches the visible word. -->
					<button
						class="btn btn-icon btn-ghost md:px-2.5"
						class:text-accent={bookmark.current}
						onclick={bookmark.toggle}
						aria-label={t('reader.bookmark')}
						title={t('reader.bookmark')}
						aria-pressed={bookmark.current}
						><Icon name="bookmark" size={18} /><span class="hidden text-small md:inline"
							>{t('reader.bookmark')}</span
						></button
					>
					{#if listen.supported && !isPhone}
						<button
							class="btn btn-icon btn-ghost md:px-2.5"
							class:text-accent={listen.status !== 'idle'}
							onclick={() => (listen.status === 'idle' ? reader?.startListening() : listen.stop())}
							aria-label={t('reader.listen')}
							aria-pressed={listen.status !== 'idle'}
							title={t('reader.listen')}
							><Icon name="headphones" size={18} /><span class="hidden text-small md:inline"
								>{t('reader.listen')}</span
							></button
						>
					{/if}
					{#if !isPhone}
						<ReaderControls />
					{/if}
				</div>
				<!-- The one "⋯" group, both bars. Its rows depend on the bar: Bookmark
				     sits in the row from `sm`, so only the phone folds it in here. -->
				<div
					class="relative shrink-0"
					use:dismissable={{ open: moreOpen, onDismiss: () => (moreOpen = false) }}
				>
					<button
						class="btn btn-icon btn-ghost min-w-11 sm:min-w-0"
						onclick={() => (moreOpen = !moreOpen)}
						aria-expanded={moreOpen}
						aria-controls={moreOpen ? 'sermon-more' : undefined}
						aria-label={t('reader.moreTools')}
						title={t('reader.moreTools')}
						><Icon name="more" size={20} class="sm:size-[18px]" /></button
					>
					{#if moreOpen}
						<!-- A labelled group, not role="menu" (no arrow-key roving) — the
						     same treatment as AccountMenu. -->
						<div id="sermon-more" class="account-menu more-group" role="group" aria-label={t('reader.moreTools')}>
							{#if isPhone}
								<button
									class="account-item more-item"
									class:text-accent={bookmark.current}
									onclick={fromMore(bookmark.toggle)}
									aria-pressed={bookmark.current}
									><Icon name="bookmark" size={20} />{bookmark.current
										? t('reader.removeBookmark')
										: t('reader.bookmark')}</button
								>
							{/if}
							<!-- Save to "My Library": the store FavoriteButton toggles. -->
							<button
								class="account-item more-item"
								class:text-accent={saved}
								onclick={fromMore(() => favorites.toggle('sermon', sermon.slug))}
								aria-pressed={saved}
								><Icon name="favorite" size={20} filled={saved} />{saved ? t('fav.saved') : t('fav.save')}</button
							>
							<button class="account-item more-item" onclick={shareFromMore}
								><Icon name="share" size={20} strokeWidth={1.7} /><span aria-live="polite"
									>{copied
										? t('share.linkCopied')
										: showTargets
											? t('share.copyLink')
											: t('reader.share')}</span
								></button
							>
							{#if showTargets}
								{#each shareTargets as st (st.name)}
									<a
										class="account-item more-item share-target"
										href={st.href}
										target={st.newTab ? '_blank' : undefined}
										rel={st.newTab ? 'noopener noreferrer' : undefined}
										onclick={() => (moreOpen = false)}>{st.name}</a
									>
								{/each}
							{/if}
							<button class="account-item more-item" onclick={fromMore(() => readerUi.toggleFocus())}
								><Icon name="maximize" size={20} />{t('reader.focus')}</button
							>
						</div>
					{/if}
				</div>
			</div>
		</div>
	</div>
{/if}

{#if readerUi.focus}
	<FocusExit />
{/if}

<!-- Jump-to-section outline panel (opened from the top bar). -->
{#if outlineOpen}
	<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
	<div class="outline-backdrop" onclick={() => (outlineOpen = false)}></div>
	<nav
		class="outline-panel"
		style={outlinePos}
		aria-label={t('sermon.outline')}
		use:focusTrap={{ onEscape: () => (outlineOpen = false) }}
	>
		<p class="outline-title eyebrow eyebrow-micro">{t('sermon.outline')}</p>
		<ul>
			{#each outline as s (s.id)}
				<li>
					<button
						class="outline-item"
						class:point={s.kind === 'point'}
						onclick={() => scrollToSection(s.id)}
					>
						{s.label}
					</button>
				</li>
			{/each}
		</ul>
	</nav>
{/if}

<!-- `--pinned-offset`: how far down the first pixel unobstructed by the sticky
     reader bar is (HEADER_OFFSET). The outline anchors below hang their
     `scroll-margin-top` off it, so a jump lands the section clear of the bar —
     the same contract the biographies/search pages use, replacing this page's
     old `scrollTo(top - HEADER_OFFSET - 8)` math. -->
<article
	class="relative mx-auto px-5 py-10"
	style="--pinned-offset: {HEADER_OFFSET}px; {readerPrefs.style}; max-width: var(--reading-measure)"
>
	<!-- Persistent outline rail (wide screens): mirrors the popover, highlighting
	     the section you're reading. The top-bar toggle takes over below 1280px.
	     It lives INSIDE the article, on a track beside the column as tall as the
	     article, and sticks within it: when it was position:fixed it sat on top
	     of the sign-up band and the footer at the end of every long sermon. -->
	{#if outline.length >= 2 && !readerUi.focus}
		<div class="outline-track">
			<nav class="outline-rail" aria-label={t('sermon.outline')}>
				<p class="outline-rail-title eyebrow eyebrow-micro">{t('sermon.outline')}</p>
				<ul>
					{#each outline as s (s.id)}
						<li>
							<button
								class="outline-rail-item"
								class:point={s.kind === 'point'}
								class:active={spy.active === s.id}
								onclick={() => scrollToSection(s.id)}
							>
								{s.label}
							</button>
						</li>
					{/each}
				</ul>
			</nav>
		</div>
	{/if}

	<!-- Not on phones: the top bar's title block already names the sermon, and
	     the trail wrapped to two lines repeating it. Only the visible trail —
	     the BreadcrumbList JSON-LD (crumbsLd) still ships. -->
	<div class="max-sm:hidden"><Breadcrumb items={crumbs} /></div>

	<LanguageFallbackNotice {fallback} alternates={hreflang.alternates} browsePath="/sermons" />

	<!-- The head sits in its plate (see SermonPlate), except in focus mode,
	     which strips the page to the prose. -->
	{#snippet head()}
		<p class="eyebrow mb-1 text-muted">
			{t('search.typeSermon')} · {readingTime(sermon.word_count)}{#if year} · {year}{/if}{#if sermon.difficulty}&nbsp;·
				<span title={t('reader.difficulty')}>{t(`reader.difficulty_${sermon.difficulty}`)}</span>{/if}
		</p>
		<h1 class="text-h1 mb-3" dir="auto" lang={contentLang(sermon.language)}>{sermon.title}</h1>

		<!-- Author row: portrait + name -->
		<a
			href={localizeHref(`/authors/${sermon.author_slug}`)}
			class="group mb-1 inline-flex items-center gap-2.5 hover:no-underline"
		>
			{#if sermon.author_photo}
				<img
					src={sermon.author_photo}
					use:hydrateSrc={{ src: sermon.author_photo }}
					alt="{t('a11y.portraitOf')} {sermon.author_name}"
					class="h-9 w-9 shrink-0 rounded-full border border-border object-cover"
					style="filter: grayscale(1); object-position: {portraitPosition(sermon.author_slug)}"
					loading="lazy"
				/>
			{:else}
				<span
					class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-accent-soft text-small font-semibold text-accent"
				>
					{initials(sermon.author_name)}
				</span>
			{/if}
			<span class="text-body font-medium text-text group-hover:text-accent"
				>{sermon.author_name}</span
			>
		</a>
	{/snippet}

	<!-- The margin is the wrapper's, not one branch's: hung off the plate alone
	     it vanished in focus mode and the head sat flush against the card below. -->
	<div class="mb-5">
		{#if readerUi.focus}
			{@render head()}
		{:else}
			<SermonPlate slug={sermon.slug} scriptureRef={sermon.scripture_ref} title={sermon.title}>{@render head()}</SermonPlate>
		{/if}
	</div>

	<!-- Preaching text: the reference, and its verse(s) when available -->
	{#if sermon.scripture_ref}
		<div class="text-card">
			<p class="text-card-eyebrow eyebrow eyebrow-micro">{t('sermon.text')}</p>
			<p class="text-card-ref">{sermon.scripture_ref}</p>
			{#if preachingText?.verses?.length}
				<p class="text-card-verse">
					{#each preachingText.verses as v (v.number)}{v.text}{' '}{/each}
				</p>
				<p class="text-card-version eyebrow eyebrow-micro">{preachingText.version}</p>
			{/if}
		</div>
	{/if}

	<!-- "In brief": an AI-drafted TL;DR so a reader knows in ten seconds
	     whether this sermon is the one they need right now. -->
	{#if sermon.summary}
		<div class="mb-8 rounded-card border border-border bg-surface p-4">
			<p class="eyebrow mb-1.5 text-accent">
				{t('sermon.inBrief')}
			</p>
			<p class="text-small leading-relaxed text-muted">{sermon.summary}</p>
		</div>
	{/if}

	<Reader
		bind:this={reader}
		kind="sermon"
		slug={sermon.slug}
		language={sermon.language}
		html={sermon.body_html}
		{cite}
		listenTitle={sermon.title}
		listenArtist={sermon.author_name}
		bind:body
		bind:frac
		finishOnEnd
	/>

	<!-- Questions for reflection: answered study questions grounded in the sermon.
	     Renders from the same `study_questions` array as the FAQPage JSON-LD, so
	     the markup never asserts a question the reader can't see. Plain text, so
	     no {@html}. Gated to reviewed-heading locales (faqItems) — see the note by
	     the derivation. -->
	{#if faqItems.length}
		<section class="mt-12 border-t border-border pt-6" aria-labelledby="questions-heading">
			<h2 id="questions-heading" class="section-heading">{t('sermon.questionsTitle')}</h2>
			<dl class="space-y-5">
				{#each faqItems as item (item.q)}
					<div>
						<dt class="text-body font-semibold text-text">{item.q}</dt>
						<dd class="mt-1 text-body leading-relaxed text-muted">{item.a}</dd>
						{#if ReflectBox}
							<dd class="mt-2">
								<ReflectBox
									compact
									prompt={t('notebook.reflectAnswerPrompt')}
									title={item.q}
									collection={sermon.title}
									source={{
										kind: 'sermon',
										slug: sermon.slug,
										order: 1,
										p: 0,
										edition: sermon.language,
										title: sermon.title,
										quote: ''
									}}
								/>
							</dd>
						{/if}
					</div>
				{/each}
			</dl>
		</section>
	{/if}

	<!-- Scripture index: the passages this sermon engages, each a jump into
	     scripture search — so scripture is a navigation surface, not just text. -->
	{#if sermon.scripture_refs?.length}
		<div class="mt-10 flex flex-wrap items-center gap-2 border-t border-border pt-5">
			<span class="eyebrow text-muted">
				{t('sermon.scriptureIndex')}
			</span>
			{#each sermon.scripture_refs as ref (ref)}
				<!-- Link to the crawlable /scripture reverse-index page when this
				     passage has one (English-only pages, so not localized); else fall
				     back to a localized search. Same resolver the body links with. -->
				<a
					href={sermon.scripture_links?.[ref] ?? localizeHref(`/search?q=${encodeURIComponent(ref)}`)}
					class="tag"
				>
					{ref}
				</a>
			{/each}
		</div>
	{/if}

	<!-- Topical shelves this sermon appears on — the same membership the author
	     and topic pages surface; a reader moved by it can find kindred works. -->
	{#if sermon.topics?.length}
		<div class="mt-4 flex flex-wrap items-center gap-2">
			<span class="eyebrow text-muted">
				{t('sermon.topics')}
			</span>
			{#each sermon.topics as topic (topic.slug)}
				<a
					href={localizeHref(`/topics/${topic.slug}`)}
					class="rounded-full bg-surface-2 px-3 py-1 text-small text-text hover:text-accent hover:no-underline"
				>
					{topic.title}
				</a>
			{/each}
		</div>
	{/if}

	<!-- Sequential prev/next through this author's sermons, so a reader who
	     finishes one keeps going instead of dead-ending at the bottom. -->
	{#if sermon.prev || sermon.next}
		<nav class="mt-12 flex gap-3 border-t border-border pt-6" aria-label={t('sermon.sequentialNav')}>
			{#if sermon.prev}
				<a
					href={localizeHref(`/sermons/${sermon.prev.slug}`)}
					class="group flex-1 rounded-card border border-border p-3 hover:border-accent hover:no-underline"
				>
					<div class="eyebrow text-muted"><Arrow back /> {t('reader.previous')}</div>
					<div class="mt-0.5 text-small font-semibold text-text group-hover:text-accent">
						<bdi>{sermon.prev.title}</bdi>
					</div>
				</a>
			{/if}
			{#if sermon.next}
				<a
					href={localizeHref(`/sermons/${sermon.next.slug}`)}
					class="group flex-1 rounded-card border border-border p-3 text-end hover:border-accent hover:no-underline"
				>
					<div class="eyebrow text-muted">{t('reader.next')} <Arrow /></div>
					<div class="mt-0.5 text-small font-semibold text-text group-hover:text-accent">
						<bdi>{sermon.next.title}</bdi>
					</div>
				</a>
			{/if}
		</nav>
	{/if}

	{#if related.length}
		<section class="mt-12 border-t border-border pt-6">
			<h2 class="section-heading">{t('book.related')}</h2>
			<ul class="space-y-2">
				{#each related as r (r.slug)}
					<li>
						<a href={localizeHref(`/sermons/${r.slug}`)} class="text-body font-medium">{r.title}</a>
						<span class="text-small text-muted"> · {r.scripture_ref} · {r.author.name}</span>
					</li>
				{/each}
			</ul>
		</section>
	{/if}

	<!-- A permission credit (`attribution`) takes precedence over the generic
	     public-domain line: these sermons are copyrighted and used by
	     permission, so the page must never label them public domain. -->
	{#if sermon.attribution}
		<p class="mt-12 border-t border-border pt-5 text-small text-muted">
			{sermon.attribution}
			{#if sermon.source_url}
				<a href={sermon.source_url} target="_blank" rel="noreferrer">SermonIndex</a>.
			{/if}
		</p>
	{:else if sermon.source_url}
		<p class="mt-12 border-t border-border pt-5 text-small text-muted">
			{t('book.publicDomain')}
			<a href={sermon.source_url} target="_blank" rel="noreferrer">{t('book.originalEdition')}</a>.
		</p>
	{/if}

	<nav class="mt-8 flex flex-wrap gap-3">
		<a href={localizeHref(`/authors/${sermon.author_slug}`)} class="btn btn-ghost"
			><Arrow back /> {t('sermon.moreFrom')} <bdi>{sermon.author_name}</bdi></a
		>
		<!-- The author's memorable lines: a bridge from the sermon to their quote
		     page. English only, as the quote pages are — mirrors the book detail's
		     link (feat/book-author-quotes-link), gate and all. -->
		{#if sermon.author_quote_count && getLang() === 'en'}
			<a href={`/quotes/${sermon.author_slug}/`} class="btn btn-ghost"
				>Quotes from {sermon.author_name} <Arrow /></a
			>
		{/if}
	</nav>
</article>

<!-- Time-remaining pill; hidden in focus and while listening. On phones the
     footer row carries the same line instead. -->
{#if !isPhone && !readerUi.focus && listen.status === 'idle' && frac < 0.99}
	<div class="min-left" aria-hidden="true">{minsLeft} {t('sermon.minLeft')}</div>
{/if}

<!-- Phone footer, in thumb reach — the chapter reader's: a scrubber, the
     minutes left, and Previous · Listen · + · Aa · Next (Previous/Next step
     through this author's sermons, as the nav at the foot of the page does).
     Hidden in focus and while listening, when the Listen bar owns the bottom. -->
{#if isPhone && !readerUi.focus && listen.status === 'idle'}
	<div class="sermon-foot-spacer" aria-hidden="true"></div>
	<div bind:this={footEl} class="sermon-foot">
		<div class="foot-fade" aria-hidden="true"></div>
		<input
			class="scrubber"
			type="range"
			min="0"
			max="1"
			step="0.005"
			value={frac}
			oninput={(e) => scrubTo(Number(e.currentTarget.value))}
			aria-label={t('progress.scrub')}
			aria-valuetext="{minsLeft} {t('sermon.minLeft')}"
		/>
		<p class="sermon-foot-meta" aria-hidden="true">{minsLeft} {t('sermon.minLeft')}</p>
		<div class="foot-actions" class:folded={foldActions}>
			{#if sermon.prev}
				<a href={localizeHref(`/sermons/${sermon.prev.slug}`)} class="foot-btn"
					><Icon name="chevron-left" size={22} /><span>{t('reader.previous')}</span></a
				>
			{:else}
				<span class="foot-btn" aria-hidden="true"></span>
			{/if}
			{#if listen.supported}
				<button class="foot-btn" onclick={() => reader?.startListening()}
					><Icon name="headphones" size={22} /><span>{t('reader.listen')}</span></button
				>
			{/if}
			<FootFeedback />
			<button
				class="foot-btn"
				onclick={() => (readerUi.panelOpen = true)}
				aria-haspopup="dialog"
				aria-expanded={readerUi.panelOpen}
				aria-label={t('reader.textSettings')}
				title={t('reader.textSettings')}><span class="foot-aa" aria-hidden="true">Aa</span></button
			>
			{#if sermon.next}
				<a href={localizeHref(`/sermons/${sermon.next.slug}`)} class="foot-btn foot-next"
					><Icon name="chevron-right" size={22} /><span>{t('reader.next')}</span></a
				>
			{:else}
				<span class="foot-btn" aria-hidden="true"></span>
			{/if}
		</div>
	</div>
{/if}

<!-- The phone text-settings sheet, opened by the footer's Aa. At page root, not
     in the top bar, which unmounts in focus mode. -->
{#if isPhone}
	<ReaderControls sheet />
{/if}

<style>
	/* --- Phone footer (below `sm`) — mirrors the chapter's .progress-foot ---- */
	.sermon-foot,
	.sermon-foot-spacer {
		display: none;
	}
	@media (max-width: 639.98px) {
		.sermon-foot {
			display: block;
			position: fixed;
			inset-inline: 0;
			bottom: 0;
			z-index: var(--z-popover);
			padding: 0.25rem 1rem calc(0.4rem + env(safe-area-inset-bottom));
			text-align: center;
			font-size: var(--fs-micro);
			color: var(--muted);
			background: color-mix(in srgb, var(--bg) 82%, transparent);
			backdrop-filter: blur(6px);
		}
		/* In-flow clearance, so the page's last lines scroll clear of the footer.
		   The measured unfolded height; the fallback covers the first frame. */
		.sermon-foot-spacer {
			display: block;
			height: var(--foot-h, calc(8rem + env(safe-area-inset-bottom)));
		}
		.foot-actions {
			display: flex;
			margin-top: 0.15rem;
		}
		.foot-actions.folded {
			display: none;
		}
	}
	/* A short fade above the footer, so a line scrolling under it dissolves
	   instead of being sliced at the bar's top edge. */
	.foot-fade {
		position: absolute;
		inset-inline: 0;
		bottom: 100%;
		height: 2.25rem;
		background: linear-gradient(to top, var(--bg), transparent);
		pointer-events: none;
	}
	.sermon-foot-meta {
		margin-top: 0.1rem;
	}
	.scrubber {
		display: block;
		width: 100%;
		margin: 0 auto;
		height: 1.1rem;
		cursor: pointer;
		accent-color: var(--accent);
		background: transparent;
	}
	/* Touch: a range input's whole height is its hit area — a ≥44px target
	   without restyling the native thumb. */
	@media (pointer: coarse) {
		.scrubber {
			height: 2.75rem;
		}
	}
	.foot-btn {
		flex: 1 1 0;
		min-height: 2.9rem;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 0.1rem;
		border-radius: var(--radius-sm);
		font-size: var(--fs-small);
		font-weight: 600;
		color: var(--text);
	}
	.foot-next {
		color: var(--accent);
	}
	.foot-aa {
		font-family: var(--font-display);
		font-size: var(--fs-h3);
		line-height: 1;
	}

	/* Scroll-progress bar: a thin accent line scaled by reading fraction. */
	/* `.min-left` lives in app.css — the biography page shows the same pill, and
	   a second copy here is how the two would drift apart. */

	/* Outline jump targets (marked by buildOutline) clear the sticky reader bar
	   when jumped to. `--pinned-offset` is set on the <article> above to
	   HEADER_OFFSET; the +0.5rem is the breathing room the old jump math added as
	   `- 8`. :global because the class is added to the injected reader HTML, and
	   sermon-only because buildOutline runs nowhere else. */
	:global(.sec-anchor) {
		scroll-margin-top: calc(var(--pinned-offset, 5rem) + 0.5rem);
	}

	/* Preaching-text card: the sermon's reference + verse(s) as an epigraph. */
	.text-card {
		margin: 0 0 2rem;
		padding: 0.85rem 1.1rem;
		border-inline-start: 3px solid var(--accent);
		border-start-end-radius: var(--radius-card);
		border-end-end-radius: var(--radius-card);
		background: var(--accent-soft);
	}
	.text-card-eyebrow {
		color: var(--accent);
	}
	.text-card-ref {
		font-family: var(--font-display);
		font-size: var(--fs-h3);
		color: var(--accent);
		margin-top: 0.1rem;
	}
	.text-card-verse {
		margin-top: 0.5rem;
		font-family: var(--font-display);
		font-style: italic;
		line-height: 1.6;
		color: var(--text);
	}
	.text-card-version {
		margin-top: 0.45rem;
		color: var(--muted);
	}

	/* --- Top bar's "⋯" group (.more-group / .more-item: app.css) ------------ */
	/* The share targets carry no icon; indent them past the icon column. */
	.more-item.share-target {
		padding-inline-start: calc(0.75rem + 20px + 0.75rem);
	}

	/* Jump-to-section outline: a light popover hung under its toggle (top and
	   inset-inline-end are set inline from the button, in toggleOutline). */
	.outline-backdrop {
		position: fixed;
		inset: 0;
		z-index: var(--z-popover);
	}
	.outline-panel {
		position: fixed;
		z-index: calc(var(--z-popover) + 1);
		width: min(20rem, calc(100vw - 1.5rem));
		max-height: 70vh;
		overflow-y: auto;
		border: 1px solid var(--border);
		border-radius: var(--radius-card);
		background: var(--surface);
		box-shadow: var(--shadow-popover);
		padding: 0.5rem;
	}
	.outline-title {
		padding: 0.35rem 0.6rem;
		color: var(--muted);
	}
	.outline-item {
		display: block;
		width: 100%;
		text-align: start;
		padding: 0.45rem 0.6rem;
		border-radius: var(--radius-sm);
		font-size: var(--fs-small);
		color: var(--text);
		line-height: 1.35;
	}
	.outline-item:hover {
		background: var(--surface-2);
		color: var(--accent);
	}
	/* Real headings sit flush; homiletic points get a subtle indent + accent. */
	.outline-item.point {
		color: var(--muted);
	}
	.outline-item.point:hover {
		color: var(--accent);
	}

	/* Persistent outline rail — hidden until there's room beside the article. */
	.outline-rail {
		display: none;
	}
	@media (min-width: 1280px) {
		/* The track spans the article's height just past its inline-end edge, so
		   the sticky rail scrolls away with the sermon's last lines. The min()
		   keeps it on screen (a 2rem gutter, room for a scrollbar) when a wide
		   reading measure leaves less margin than the rail needs — as the fixed
		   rail's max(1rem, …) did — instead of opening a horizontal scroll. */
		.outline-track {
			position: absolute;
			inset-block: 0;
			inset-inline-start: min(calc(100% + 1rem), calc(50% + 50vw - 16rem));
			width: 14rem;
		}
		.outline-rail {
			display: block;
			position: sticky;
			top: 5rem;
			max-height: calc(100vh - 7rem);
			overflow-y: auto;
			z-index: 5;
		}
		/* The top-bar toggle is redundant once the rail is visible. */
		.outline-toggle-btn {
			display: none;
		}
	}
	.outline-rail-title {
		padding: 0 0.6rem 0.4rem;
		color: var(--muted);
	}
	.outline-rail-item {
		display: block;
		width: 100%;
		text-align: start;
		padding: 0.3rem 0.6rem;
		border-inline-start: 2px solid transparent;
		font-size: var(--fs-small);
		line-height: 1.35;
		color: var(--muted);
		transition: color var(--duration-fast) ease;
	}
	.outline-rail-item:hover {
		color: var(--accent);
	}
	.outline-rail-item.point {
		padding-inline-start: 1.1rem;
	}
	.outline-rail-item.active {
		color: var(--accent);
		border-inline-start-color: var(--accent);
		font-weight: 600;
	}
</style>
