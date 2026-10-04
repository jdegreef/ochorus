<script lang="ts">
	import type { ScripturePageEntry } from '$lib/library-public';
	import { scriptureBookHref, scripturePageHref, searchPage, SCRIPTURE_OG } from '$lib/library-public';
	import { goto } from '$app/navigation';
	import { SvelteSet } from 'svelte/reactivity';
	import type { Snapshot } from './$types';
	import { SITE_URL } from '$lib/config';
	import { breadcrumbLd, collectionPage, hreflangFor } from '$lib/seo';
	import { groupScripture, heatScale, HEAT_LEVELS, mayBeReference, mostCited } from '$lib/scriptureIndex';
	import { searchHref } from '$lib/searchState';
	import { localizeHref } from '$lib/href';
	import { scrollSpy, realignHashOnMeasure, subnavOffset } from '$lib/scrollSpy.svelte';
	import { tabStrip } from '$lib/actions/tabStrip';
	import { mediaFlag } from '$lib/mediaFlag.svelte';
	import Seo from '$lib/components/Seo.svelte';
	import PageHeader from '$lib/components/PageHeader.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import ScriptureChapterChips from '$lib/components/ScriptureChapterChips.svelte';
	import { i18n } from '$lib/i18n.svelte';

	// English-only; see the note on the chapter page.
	let { data } = $props();
	const pages = $derived<ScripturePageEntry[]>(data.pages);
	const loadError = $derived<boolean>(data.loadError);
	const t = i18n.t;

	// The books of the Bible in canonical order, grouped into their sections
	// (Law, History, … Paul's Letters), each carrying its chapter pages and its
	// most-cited verse pages. This is what makes the graph navigable rather than
	// a list of URLs only a crawler ever sees: from here every chapter page is
	// one click, and the verses readers remember are one click too.
	const sections = $derived(groupScripture(pages));
	// The sticky section bar, when there are sections to jump between.
	const showSubnav = $derived(sections.length >= 2);
	const books = $derived(sections.flatMap((s) => s.books));
	const verseCount = $derived(pages.filter((p) => p.verse !== null).length);

	// Every chapter chip is shaded by how many passages cite it, cut by rank
	// (see heatScale) so the scale holds as the library grows. The count used
	// to live only in a hover tooltip, which touch readers never see.
	const heat = $derived(heatScale(books.flatMap((b) => b.chapters.map((c) => c.count))));
	// Looked up once: the template calls this for every chip and verse link.
	const passagesTpl = $derived(t('scripture.passagesCount'));
	const passages = (n: number) => passagesTpl.replace('%count%', String(n));

	// "Go to a passage": hand the reader's reference to the search API's
	// scripture resolver — the server parses it (pythonbible: "Rom 8:28",
	// "Ps 23", "1 Cor 13"; English book names, as the page is English-only) and
	// answers only with a page that was actually built, verse page first, then
	// its chapter. No second parser here to drift from it. The form's
	// action=/search is the fallback before hydration.
	//
	// Anything else — a reference with no page, plain words, an API failure —
	// goes to the full search. That is the one search the admin report logs, so a
	// passage readers ask for that has no page shows up there with its true
	// result count, did-you-mean and click data, and the reader sees whatever the
	// library does say about it instead of a dead end. (The ?type=scripture
	// lookup itself stays unlogged, like every type= request.)
	let findQ = $state('');
	let finding = $state(false);
	// Bumped by every new lookup and every edit, so a slow reply for a query the
	// reader has since replaced is dropped instead of navigating.
	let findSeq = 0;
	function editFind() {
		findSeq++;
		finding = false;
	}
	async function find(e: SubmitEvent) {
		e.preventDefault();
		const q = findQ.trim();
		// Search ignores anything shorter (the input's minlength says so first).
		if (q.length < 2) return;
		const seq = ++findSeq;
		finding = true;
		let hit;
		if (mayBeReference(q)) {
			try {
				// type=scripture returns at most one row, and only scripture rows.
				[hit] = (await searchPage(q, 'en', 'scripture')).results;
			} catch {
				// Fall through to the full search, which has its own error and retry.
			}
		}
		if (seq !== findSeq) return;
		// Kept busy until the navigation lands, so Go can't fire it twice.
		await goto(
			hit?.type === 'scripture'
				? scripturePageHref(hit.book_slug, hit.chapter, hit.verse)
				: localizeHref(searchHref(q))
		);
		if (seq === findSeq) finding = false;
	}

	// A starting point for a reader who arrives without a passage in mind: the
	// chapters the writers return to most.
	const TOP_CHAPTERS = 8;
	const top = $derived(mostCited(pages, TOP_CHAPTERS));

	const sectionId = (key: string) => `section-${key}`;

	// On a phone, each book collapses to one row (name + chapter count) that a
	// tap opens: at 44px touch targets the full index runs to dozens of screens.
	// The breakpoint is NARROW here and `max-width: 34rem` in the CSS below; keep
	// them in step. Collapsing starts in CSS (`.books-pending`, before the page
	// hydrates) so a phone never lays the page out open and then shrinks it under
	// the reader or a #section jump; a <noscript> style reopens everything for a
	// reader without JS. Once hydrated, `hidden="until-found"` takes over, so
	// find-in-page still reaches a collapsed book's chapters and opens it.
	// `narrow` is mediaFlag (hydration-safe: false in the prerendered markup).
	const NARROW = '(max-width: 34rem)';
	const narrowQuery = mediaFlag(NARROW);
	const narrow = $derived(narrowQuery.matches);
	// "Has mounted" (not a media query, so not mediaFlag): flips in the same
	// post-hydration flush as `narrow`, so `.books-pending` hands over to the
	// `hidden` attribute in one frame.
	let hydrated = $state(false);
	$effect(() => {
		hydrated = true;
	});
	const openBooks = new SvelteSet<string>();
	const toggleBook = (slug: string) => (openBooks.has(slug) ? openBooks.delete(slug) : openBooks.add(slug));
	const chapterCount = (n: number) => `${n} ${n === 1 ? t('book.chapterOne') : t('book.chaptersMany')}`;

	// Keep the open books across Back from a chapter page, so the scroll position
	// SvelteKit restores still matches the layout it was saved against.
	export const snapshot: Snapshot<string[]> = {
		capture: () => [...openBooks],
		restore: (slugs) => {
			openBooks.clear();
			for (const slug of slugs) openBooks.add(slug);
		}
	};
	const sectionName = (key: string) => t(`scripture.section.${key}`);

	// Sticky jump bar over the sections, the author page's pattern: it pins under
	// the app nav, its height feeds `--pinned-offset`, and the scroll-spy lights
	// the section in view. No-JS / prerender: the links still jump.
	let subnavH = $state(0);
	// A cold #section load jumps against the bar's estimate; re-land it once measured.
	realignHashOnMeasure(() => subnavH);
	const spy = scrollSpy(() => sections.map((s) => sectionId(s.key)));

	const path = '/scripture/';
	const canonical = `${SITE_URL}${path}`;
	const hreflang = hreflangFor(path, ['en']);
	const title = 'Scripture in the Christian classics — Ochorus';
	const description = $derived(
		`Browse ${pages.length - verseCount} chapters of the Bible and see which passages ` +
			'in the classics treat them — every citation quoted and linked to its source.'
	);
	const crumbs = $derived([
		{ name: t('common.home'), href: '/' },
		{ name: t('reader.scripture'), href: path }
	]);
	const crumbsLd = $derived(breadcrumbLd(crumbs));

	// The same CollectionPage → ItemList every sibling hub carries (books, plans,
	// topics, sermons, …): the books of the Bible in canonical order, each item
	// its /scripture/<book>/ page — the shelf's roster, not an opaque grid a
	// crawler can only guess at.
	const collectionLd = $derived(
		collectionPage({
			name: 'Scripture in the Christian classics',
			description,
			url: canonical,
			items: books.map((b) => ({
				name: b.title,
				url: scriptureBookHref(b.slug)
			}))
		})
	);
</script>

<Seo
	{title}
	{description}
	{canonical}
	{hreflang}
	structuredData={[crumbsLd, collectionLd]}
	{...SCRIPTURE_OG}
/>

<!-- --pinned-offset: how far down the first pixel unobstructed by both the app
     nav and the section jump bar is; the section anchors read it for
     scroll-margin so a jump lands below the bars. Same contract as the author
     page. -->
<svelte:head>
	<noscript><style>.books-pending .book-body { display: block !important; }</style></noscript>
</svelte:head>

<div class="page-col px-5 py-10" class:books-pending={!hydrated} style="--pinned-offset: calc(var(--appnav-h, 0px) + {subnavOffset(showSubnav, subnavH)}px)">
	<!-- No visible breadcrumb: a top-level hub's only trail is Home > <this>
	     — Home is already the logo, <this> restates the H1 below, so it
	     carries nothing. The BreadcrumbList JSON-LD stays in the head; the
	     page's position is true even when we don't draw it. -->
	<PageHeader
		title={t('scripture.pageTitle')}
		tagline={t('scripture.tagline')}
	/>

	{#if loadError}
		<EmptyState message={t('common.loadError')} onRetry />
	{:else if !books.length}
		<EmptyState message={t('scripture.empty')} />
	{:else}
		<form class="find" method="get" action={localizeHref('/search')} role="search" onsubmit={find}>
			<label for="scripture-find" class="find-label">{t('scripture.findLabel')}</label>
			<div class="find-row">
				<input
					id="scripture-find"
					name="q"
					type="search"
					class="field"
					autocomplete="off"
					required
					minlength={2}
					enterkeyhint="go"
					placeholder={t('scripture.findPlaceholder')}
					bind:value={findQ}
					oninput={editFind}
				/>
				<button type="submit" class="btn btn-primary" disabled={finding} aria-busy={finding}>
					{t('scripture.findGo')}
				</button>
			</div>
		</form>

		<section class="top" aria-labelledby="top-heading">
			<h2 id="top-heading" class="section-label">{t('scripture.mostCited')}</h2>
			<ol class="top-list">
				{#each top as c (`${c.slug}-${c.chapter}`)}
					<li>
						<a class="top-card" href={scripturePageHref(c.slug, c.chapter, null)}>
							<span class="top-ref">{c.title} {c.chapter}</span>
							<span class="top-count">{passages(c.count)}</span>
						</a>
					</li>
				{/each}
			</ol>
		</section>

		{#if showSubnav}
			<nav
				bind:clientHeight={subnavH}
				class="sections-nav sticky z-(--z-pinned) mt-10 border-b border-border bg-bg"
				style="top: var(--appnav-h, 0px)"
				aria-label={t('a11y.pageSections')}
			>
				<ul class="tab-strip flex gap-1" use:tabStrip={spy.active}>
					{#each sections as s (s.key)}
						<li>
							<a
								href="#{sectionId(s.key)}"
								class="subnav-link"
								class:is-active={spy.active === sectionId(s.key)}
								aria-current={spy.active === sectionId(s.key) ? 'true' : undefined}
								onclick={(e) => spy.jump(e, sectionId(s.key))}>{sectionName(s.key)}</a
							>
						</li>
					{/each}
				</ul>
			</nav>
		{/if}

		<p class="legend" aria-hidden="true">
			<span>{t('scripture.heatFewer')}</span>
			{#each Array.from({ length: HEAT_LEVELS }, (_, i) => i) as level (level)}
				<span class="swatch heat-{level}"></span>
			{/each}
			<span>{t('scripture.heatMore')}</span>
		</p>

		{#each sections as s, i (s.key)}
			<section id={sectionId(s.key)} class="bible-section" aria-labelledby="{sectionId(s.key)}-h">
				{#if s.key !== 'other' && s.testament !== sections[i - 1]?.testament}
					<p class="testament eyebrow">
						{t(s.testament === 'old' ? 'scripture.oldTestament' : 'scripture.newTestament')}
					</p>
				{/if}
				<h2 id="{sectionId(s.key)}-h" class="section-label">{sectionName(s.key)}</h2>
				{#each s.books as book (book.slug)}
					{@const collapsed = narrow && !openBooks.has(book.slug)}
					<div class="book">
						<h3 class="bname">
							{#if narrow}
								<button
									type="button"
									class="book-toggle"
									aria-expanded={!collapsed}
									aria-controls="book-{book.slug}"
									onclick={() => toggleBook(book.slug)}
								>
									<span>{book.title}</span>
									<!-- Not part of the heading's name: a screen reader browsing by
									     headings hears the book, not a count. -->
									<span class="book-total" aria-hidden="true">{chapterCount(book.chapters.length)}</span>
									<svg class="chev" viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"
										><path d="M4 6l4 4 4-4" fill="none" stroke="currentColor" stroke-width="1.75" /></svg
									>
								</button>
							{:else}
								<a class="bname-link" href={scriptureBookHref(book.slug)}>{book.title}</a>
							{/if}
						</h3>
						<div
							id="book-{book.slug}"
							class="book-body min-w-0"
							hidden={collapsed ? 'until-found' : undefined}
							onbeforematch={() => openBooks.add(book.slug)}
						>
							<ScriptureChapterChips {book} chapters={book.chapters} {heat} {passages} />
							{#if book.topVerses.length}
								<p class="verses">
									<span class="verses-label">{t('scripture.topVerses')}</span>
									{#each book.topVerses as v (`${v.chapter}:${v.verse}`)}
										<a
											href={scripturePageHref(book.slug, v.chapter, v.verse)}
											title={passages(v.count)}
											aria-label="{book.title} {v.chapter}:{v.verse}, {passages(v.count)}"
											>{v.chapter}:{v.verse}</a
										>
									{/each}
								</p>
							{/if}
							<!-- On a phone the name is the open/close toggle, so the book's own
							     page gets a link inside the opened row instead. -->
							{#if narrow}
								<a class="book-link" href={scriptureBookHref(book.slug)}
									>{t('scripture.bookOverview').replace('%book%', () => book.title)}</a
								>
							{/if}
						</div>
					</div>
				{/each}
			</section>
		{/each}
	{/if}
</div>

<style>
	/* "Go to a passage" — one field and a button, above the most-cited cards. */
	.find {
		margin: 0.25rem 0 2rem;
		max-width: 32rem;
	}
	.find-label {
		display: block;
		margin-bottom: 0.4rem;
		font-size: var(--fs-small);
		font-weight: 600;
	}
	.find-row {
		display: flex;
		gap: 0.5rem;
	}
	.find-row .field {
		flex: 1;
		min-width: 0;
	}
	/* Most-cited chapters: a wrapping grid of small cards, the hub's way in for a
	   reader who arrives without a passage in mind. */
	.top {
		margin-top: 0.5rem;
	}
	.top-list {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(10.5rem, 1fr));
		gap: 0.6rem;
	}
	.top-card {
		display: flex;
		flex-direction: column;
		gap: 0.15rem;
		height: 100%;
		padding: 0.7rem 0.9rem;
		border: 1px solid var(--color-border);
		border-radius: var(--radius-sm);
		background: var(--color-surface);
		color: var(--color-text);
		text-decoration: none;
	}
	.top-card:hover {
		border-color: var(--color-accent-soft-border);
		background: var(--color-accent-soft);
	}
	.top-ref {
		font-family: var(--font-display);
		font-size: var(--fs-h3);
		font-weight: 600;
		line-height: 1.25;
	}
	.top-count {
		font-size: var(--fs-small);
		font-variant-numeric: tabular-nums;
		color: var(--color-muted);
	}

	/* Section jump bar — the author page's sub-nav recipe. */
	.sections-nav {
		padding-block: 0.35rem 0;
	}
	.sections-nav ul {
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.legend {
		display: flex;
		align-items: center;
		justify-content: flex-end;
		gap: 0.3rem;
		margin: 0.75rem 0 0;
		font-size: var(--fs-micro);
		color: var(--color-muted);
	}
	.swatch {
		width: 1.1rem;
		height: 0.75rem;
		border-radius: 3px;
	}
	.legend span:first-child {
		margin-inline-end: 0.2rem;
	}
	.legend span:last-child {
		margin-inline-start: 0.2rem;
	}

	.bible-section {
		margin-top: 2rem;
		scroll-margin-top: calc(var(--pinned-offset, 5rem) + 0.5rem);
	}
	.testament {
		margin: 0 0 0.35rem;
		color: var(--color-accent);
	}
	.book {
		display: grid;
		grid-template-columns: minmax(8rem, 11rem) 1fr;
		gap: 0.75rem;
		align-items: baseline;
		padding: 0.6rem 0;
		border-top: 1px solid var(--color-border);
	}
	/* `max-width: 34rem` is NARROW in the script; keep them in step. */
	@media (max-width: 34rem) {
		.book {
			grid-template-columns: 1fr;
			gap: 0.35rem;
		}
		/* Collapsed from first paint, before hydration hands over to `hidden`. */
		.books-pending .book-body {
			display: none;
		}
	}
	.bname {
		margin: 0;
		font-size: var(--fs-body);
		font-weight: 600;
	}
	.bname-link {
		color: inherit;
		text-decoration: none;
	}
	.bname-link:hover {
		text-decoration: underline;
	}
	.book-link {
		display: inline-flex;
		align-items: center;
		min-height: 2.75rem;
		font-size: var(--fs-small);
		font-weight: 500;
		color: var(--color-accent);
		text-decoration: none;
	}
	/* The phone-only toggle: the whole row is the target, name at the start,
	   passage total and chevron at the end. */
	.book-toggle {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		width: 100%;
		min-height: 2.75rem;
		padding: 0;
		border: 0;
		background: none;
		font: inherit;
		color: inherit;
		text-align: start;
		cursor: pointer;
	}
	.book-total {
		margin-inline-start: auto;
		font-family: var(--font-sans);
		font-size: var(--fs-small);
		font-weight: 400;
		font-variant-numeric: tabular-nums;
		color: var(--color-muted);
	}
	.chev {
		flex: none;
		color: var(--color-muted);
		transition: transform 0.15s;
	}
	.book-toggle[aria-expanded='true'] .chev {
		transform: rotate(180deg);
	}
	@media (prefers-reduced-motion: reduce) {
		.chev {
			transition: none;
		}
	}
	/* The book's most-quoted verse pages, under its chapters. */
	.verses {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: 0.3rem 0.6rem;
		margin: 0.45rem 0 0;
		font-size: var(--fs-small);
	}
	.verses-label {
		color: var(--color-muted);
	}
	.verses a {
		font-variant-numeric: tabular-nums;
		font-weight: 500;
		color: var(--color-accent);
		text-decoration: none;
	}
	.verses a:hover {
		text-decoration: underline;
	}
	/* Bare text links ~20px tall: on touch, pad them to a 32px target. */
	@media (pointer: coarse) {
		.verses a {
			display: inline-flex;
			align-items: center;
			min-height: 2rem;
			padding-inline: 0.15rem;
		}
	}
</style>
