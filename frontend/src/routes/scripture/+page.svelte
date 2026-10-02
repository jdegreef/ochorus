<script lang="ts">
	import type { ScripturePageEntry } from '$lib/library-public';
	import { scripturePageHref, searchPage } from '$lib/library-public';
	import { goto } from '$app/navigation';
	import { SvelteSet } from 'svelte/reactivity';
	import { SITE_URL } from '$lib/config';
	import { breadcrumbLd, collectionPage, hreflangFor } from '$lib/seo';
	import { groupScripture, heatScale, HEAT_LEVELS, mostCited } from '$lib/scriptureIndex';
	import { scrollSpy, jumpToSection } from '$lib/scrollSpy.svelte';
	import { tabStrip } from '$lib/actions/tabStrip';
	import Seo from '$lib/components/Seo.svelte';
	import PageHeader from '$lib/components/PageHeader.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
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
	let findQ = $state('');
	let finding = $state(false);
	let notFound = $state('');
	// Bumped by every new lookup and every edit, so a slow reply for a query the
	// reader has since replaced is dropped instead of navigating or showing a miss.
	let findSeq = 0;
	const searchAllHref = (q: string) => `/search?q=${encodeURIComponent(q)}`;
	function editFind() {
		findSeq++;
		finding = false;
		notFound = '';
	}
	async function find(e: SubmitEvent) {
		e.preventDefault();
		const q = findQ.trim();
		if (!q) return;
		const seq = ++findSeq;
		finding = true;
		notFound = '';
		let hit;
		try {
			// type=scripture returns at most one row, and only scripture rows.
			[hit] = (await searchPage(q, 'en', 'scripture')).results;
		} catch {
			// The API failed: the full search page has its own error and retry.
			if (seq === findSeq) await goto(searchAllHref(q));
			return;
		} finally {
			if (seq === findSeq) finding = false;
		}
		if (seq !== findSeq) return;
		if (hit?.type === 'scripture') await goto(scripturePageHref(hit.book_slug, hit.chapter, hit.verse));
		else notFound = q;
	}

	// A starting point for a reader who arrives without a passage in mind: the
	// chapters the writers return to most.
	const TOP_CHAPTERS = 8;
	const top = $derived(mostCited(pages, TOP_CHAPTERS));

	const sectionId = (key: string) => `section-${key}`;

	// On a phone, each book collapses to one row (name + passage total) that a
	// tap opens: at 44px touch targets the full index runs to dozens of screens.
	// A $state flipped in an effect, NOT svelte/reactivity's MediaQuery, for the
	// book reader's reason: MediaQuery reads matchMedia during hydration and
	// would disagree with the prerendered markup. So the prerendered page (and a
	// reader without JS) shows every book open; the links are always in the HTML.
	let narrow = $state(false);
	$effect(() => {
		const mq = window.matchMedia('(max-width: 34rem)');
		const sync = () => (narrow = mq.matches);
		sync();
		mq.addEventListener('change', sync);
		return () => mq.removeEventListener('change', sync);
	});
	const openBooks = new SvelteSet<string>();
	const toggleBook = (slug: string) => (openBooks.has(slug) ? openBooks.delete(slug) : openBooks.add(slug));
	const bookTotal = (chapters: { count: number }[]) => chapters.reduce((n, c) => n + c.count, 0);
	const sectionName = (key: string) => t(`scripture.section.${key}`);

	// Sticky jump bar over the sections, the author page's pattern: it pins under
	// the app nav, its height feeds `--pinned-offset`, and the scroll-spy lights
	// the section in view. No-JS / prerender: the links still jump.
	let subnavH = $state(0);
	const spy = scrollSpy(() => sections.map((s) => sectionId(s.key)));
	function jumpTo(e: MouseEvent, id: string) {
		e.preventDefault();
		spy.set(id);
		jumpToSection(id);
		// Keep SvelteKit's state on the entry: replacing it with null erases the
		// router's history index, and Back from a chapter page then changes only
		// the URL. (The book page does the same.)
		history.replaceState(history.state, '', `#${id}`);
	}

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
	// topics, sermons, …): the books of the Bible in canonical order. There is no
	// per-book index route, so each item points at the book's first chapter page —
	// the shelf's roster, not an opaque grid a crawler can only guess at.
	const collectionLd = $derived(
		collectionPage({
			name: 'Scripture in the Christian classics',
			description,
			url: canonical,
			items: books.map((b) => ({
				name: b.title,
				url: scripturePageHref(b.slug, b.chapters[0].chapter, null)
			}))
		})
	);
</script>

<Seo {title} {description} {canonical} {hreflang} structuredData={[crumbsLd, collectionLd]} />

<!-- --pinned-offset: how far down the first pixel unobstructed by both the app
     nav and the section jump bar is; the section anchors read it for
     scroll-margin so a jump lands below the bars. Same contract as the author
     page. -->
<div class="page-col px-5 py-10" style="--pinned-offset: calc(var(--appnav-h, 0px) + {subnavH}px)">
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
		<form class="find" method="get" action="/search" role="search" onsubmit={find}>
			<label for="scripture-find" class="find-label">{t('scripture.findLabel')}</label>
			<div class="find-row">
				<input
					id="scripture-find"
					name="q"
					type="search"
					class="field"
					autocomplete="off"
					enterkeyhint="go"
					placeholder={t('scripture.findPlaceholder')}
					bind:value={findQ}
					oninput={editFind}
				/>
				<button type="submit" class="btn btn-primary" disabled={finding} aria-busy={finding}>
					{t('scripture.findGo')}
				</button>
			</div>
			{#if notFound}
				<p class="find-none" role="status">
					{t('scripture.findNone').replace('%ref%', () => notFound)}
					<a href={searchAllHref(notFound)}>{t('scripture.findSearchAll')}</a>
				</p>
			{/if}
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

		{#if sections.length >= 2}
			<nav
				bind:clientHeight={subnavH}
				class="sections-nav sticky z-20 mt-10 border-b border-border bg-bg"
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
								onclick={(e) => jumpTo(e, sectionId(s.key))}>{sectionName(s.key)}</a
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
									<span class="book-total">{passages(bookTotal(book.chapters))}</span>
									<svg class="chev" viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"
										><path d="M4 6l4 4 4-4" fill="none" stroke="currentColor" stroke-width="1.75" /></svg
									>
								</button>
							{:else}
								{book.title}
							{/if}
						</h3>
						<div id="book-{book.slug}" class="min-w-0" hidden={collapsed}>
							<ul class="chapters">
								{#each book.chapters as c (c.chapter)}
									<li>
										<a
											href={scripturePageHref(book.slug, c.chapter, null)}
											class="heat-{heat(c.count)}"
											title={passages(c.count)}
											aria-label="{book.title} {c.chapter}, {passages(c.count)}">{c.chapter}</a
										>
									</li>
								{/each}
							</ul>
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
	.find-none {
		margin: 0.5rem 0 0;
		font-size: var(--fs-small);
		color: var(--color-muted);
	}
	.find-none a {
		color: var(--color-accent);
		white-space: nowrap;
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
	.subnav-link {
		display: inline-block;
		padding: 0.5rem 0.75rem;
		border-bottom: 2px solid transparent;
		margin-bottom: -1px; /* overlap the bar's own border so the underline meets it */
		font-size: var(--fs-small);
		font-weight: 500;
		white-space: nowrap;
		color: var(--color-muted);
		text-decoration: none;
	}
	.subnav-link:hover {
		color: var(--color-text);
	}
	.subnav-link.is-active {
		color: var(--color-accent);
		border-bottom-color: var(--color-accent);
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
	@media (max-width: 34rem) {
		.book {
			grid-template-columns: 1fr;
			gap: 0.35rem;
		}
	}
	.bname {
		margin: 0;
		font-size: var(--fs-body);
		font-weight: 600;
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
	.chapters {
		list-style: none;
		display: flex;
		flex-wrap: wrap;
		gap: 0.35rem;
		margin: 0;
		padding: 0;
	}
	.chapters a {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		min-width: 2rem;
		padding: 0.15rem 0.45rem;
		text-align: center;
		font-variant-numeric: tabular-nums;
		font-size: var(--fs-small);
		border-radius: var(--radius-sm);
		color: var(--color-text);
		text-decoration: none;
	}
	/* On touch, each chapter number is a 44px square: 708 of them were 26px
	   tall, a grid you had to aim at. */
	@media (pointer: coarse) {
		.chapters a {
			min-width: 2.75rem;
			min-height: 2.75rem;
		}
	}

	/* Heat: how many passages cite the chapter. Levels 0–3 keep body ink on an
	   accent wash light enough to hold it (≥4.5:1 in every theme); the top level
	   is the solid accent with its own contrast ink. */
	.heat-0 {
		background: var(--color-surface-2);
	}
	.heat-1 {
		background: color-mix(in srgb, var(--color-accent) 12%, var(--color-surface-2));
	}
	.heat-2 {
		background: color-mix(in srgb, var(--color-accent) 24%, var(--color-surface-2));
	}
	.heat-3 {
		background: color-mix(in srgb, var(--color-accent) 40%, var(--color-surface-2));
	}
	.heat-4 {
		background: var(--color-accent);
	}
	/* Its ink needs `.chapters a` specificity to beat that rule's body colour. */
	.chapters a.heat-4 {
		color: var(--color-accent-contrast);
		font-weight: 600;
	}
	.chapters a:hover {
		outline: 2px solid var(--color-accent);
		outline-offset: 1px;
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
