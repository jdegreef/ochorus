<script lang="ts">
	import { formatLifespan } from '$lib/library-public';
	import { SITE_URL } from '$lib/config';
	import { localizeHref } from '$lib/href';
	import { i18n } from '$lib/i18n.svelte';
	import { lang } from '$lib/lang.svelte';
	import { hreflangAll, itemList } from '$lib/seo';
	import { authorIndex, filingKey, filterIndex, indexRows, withPin } from '$lib/authorIndex';
	import { BIBLE_PATH, bibleIn, isBibleBook } from '$lib/bible';
	import { foldText } from '$lib/searchNormalize';
	import { SvelteSet } from 'svelte/reactivity';
	import { tick } from 'svelte';
	import { scrollEdges } from '$lib/actions/scrollEdges';
	import { ORIGINALS_SLUG } from '$lib/originals';
	import { OWB_SLUG } from '$lib/openWordBible';
	import type { PageData } from './$types';
	import Seo from '$lib/components/Seo.svelte';
	import PageHeader from '$lib/components/PageHeader.svelte';
	import LibraryTabs from '$lib/components/LibraryTabs.svelte';
	import GroupHeading from '$lib/components/GroupHeading.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import FilterSummary from '$lib/components/FilterSummary.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import Portrait from '$lib/components/Portrait.svelte';
	import FilterBar from '$lib/components/FilterBar.svelte';
	import AzRail from '$lib/components/AzRail.svelte';
	import Arrow from '$lib/components/Arrow.svelte';
	import AuthorsFaceWall from '$lib/components/AuthorsFaceWall.svelte';
	import { meetFirst, timeline } from '$lib/authorsMeet';
	import { ERA_HUE } from '$lib/eras';

	// The library A–Z: every writer and, under each, every book of theirs in
	// this language — see $lib/authorIndex for why this page exists. It used to
	// be a hidden, noindexed crawl anchor that redirected to /biographies on
	// mount; the same complete link set is now the page itself, visible and
	// indexable. Deliberately NOT paginated: it must stay complete, for readers
	// and for the prerender crawl (svelte.config.js seeds it per locale).
	let { data }: { data: PageData } = $props();
	const t = i18n.t;

	// The imprint and the translation are not people and have no author page —
	// /originals and /open-word-bible instead.
	const groups = $derived(
		authorIndex(data.authors, data.books, lang.current, [ORIGINALS_SLUG, OWB_SLUG])
	);
	const rowGroups = $derived(indexRows(groups));
	const writerCount = $derived(groups.reduce((n, g) => n + g.entries.length, 0));

	// The face wall: the writers with the most books in this language who have a
	// real portrait, then laid out earliest-born first so the centuries run
	// across it. 34 is two full rows on a laptop (a phone shows the first 30,
	// five rows of six), and stays a picture, not a second index.
	const FACES = 34;
	const faces = $derived(
		groups
			.flatMap((g) => g.entries)
			.filter((e) => e.author.photo_url)
			.sort((a, b) => b.books.length - a.books.length || a.author.name.localeCompare(b.author.name))
			.slice(0, FACES)
			.map((e) => e.author)
			.sort((a, b) => (a.birth_year ?? 9999) - (b.birth_year ?? 9999))
	);

	// Two doors in above the A–Z: a few writers to meet first, each with the
	// book to open, and every pictured writer on one line by era.
	const listed = $derived(groups.flatMap((g) => g.entries).map((e) => e.author));
	const meet = $derived(meetFirst(listed, data.books));
	const eras = $derived(timeline(listed));

	// The filter only narrows what is SHOWN, after hydration: the prerendered
	// HTML is always the full, unfiltered index (the query starts blank).
	let query = $state('');
	// A tradition or region chip (the Biographies hubs: "Puritans", "East
	// Africa"), narrowing the list to that hub's writers. Same rule as the query:
	// the prerendered HTML is always the whole index.
	let hub = $state<string | null>(null);
	const hubMembers = $derived(
		hub ? new Set(data.hubs.find((h) => h.slug === hub)?.members ?? []) : null
	);
	const shownGroups = $derived.by(() => {
		const byQuery = filterIndex(rowGroups, query);
		if (!hubMembers) return byQuery;
		return byQuery
			.map((g) => ({ ...g, entries: g.entries.filter((e) => hubMembers.has(e.author.slug)) }))
			.filter((g) => g.entries.length);
	});
	const filtering = $derived(query.trim() !== '' || hub !== null);
	const clearFilters = () => {
		query = '';
		hub = null;
	};
	const shownWriters = $derived(shownGroups.reduce((n, g) => n + g.entries.length, 0));

	// The Bible: its books have no writer here (the translation is skipped, like
	// the imprint), so its place in the A–Z is ONE pinned entry, filed as "Bible,
	// The" among the writers, opening the hub ($lib/bible splitBible — the /books
	// shelf keeps them out the same way). Only where the hub exists (`bibleIn`);
	// the filter keeps it for a query its name matches.
	const bibleCount = $derived(bibleIn(lang.current) ? data.books.filter(isBibleBook).length : 0);
	const biblePin = $derived.by(() => {
		const name = t('nav.bible');
		const q = foldText(query.trim());
		if (!bibleCount || hub || (q && !foldText(name).includes(q))) return null;
		return { key: filingKey(name), name, count: bibleCount };
	});
	const listedGroups = $derived(
		withPin(shownGroups, biblePin, (e) => filingKey(e.author.name), lang.current)
	);

	// A long list shows its first ROWS_SHOWN lines, the rest behind "Show N more".
	// Only collapsed when that hides at least two — "Show 1 more" saves nothing.
	// The hidden lines stay in the markup (`hidden`), so every book is still
	// linked from the prerendered page.
	const ROWS_SHOWN = 5;
	const expanded = new SvelteSet<string>();
	const collapsible = (rows: number) => !filtering && rows > ROWS_SHOWN + 1;
	const collapses = (slug: string, rows: number) => collapsible(rows) && !expanded.has(slug);
	// Collapsing a long list pulls the button up by the height of the rows it
	// hid; scroll by the same amount so it stays under the reader's pointer.
	async function toggle(slug: string, button: HTMLElement) {
		const before = button.getBoundingClientRect().top;
		if (expanded.has(slug)) expanded.delete(slug);
		else expanded.add(slug);
		await tick();
		window.scrollBy({ top: button.getBoundingClientRect().top - before, behavior: 'instant' });
	}

	// The A–Z rail is the full alphabet, so its shape doesn't change with the
	// language or the filter; letters with nobody under them are dimmed.
	const AZ = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('');
	const anchor = (letter: string) => `letter-${letter === '#' ? 'other' : letter}`;
	const present = $derived(new Set(listedGroups.map((g) => g.letter)));
	const rail = $derived(present.has('#') ? [...AZ, '#'] : AZ);
	// Joined so the effect below re-binds only when the SET of letters changes,
	// not on every keystroke that rebuilds `shownGroups`.
	const letterIds = $derived(listedGroups.map((g) => anchor(g.letter)).join(' '));

	/** Height of the pinned controls bar — jumps land below it. */
	let pinnedH = $state(0);
	let controlsEl = $state<HTMLElement>();
	let railEl = $state<HTMLElement>();

	// The lit letter: the last section whose top has scrolled up to the pinned
	// bar's bottom edge — the same line a jump lands a heading on (the
	// --pinned-offset scroll-margin). Measured from the bar itself, not a
	// viewport percentage (scrollSpy's band), because the bar's height varies
	// with the wrap and the filter summary, and a short letter (M: four names)
	// landed under a fixed band lit the one before it.
	let active = $state('');
	/** The rail's letter for the lit section id. */
	const activeLetter = $derived(active === 'letter-other' ? '#' : active.replace(/^letter-/, ''));
	$effect(() => {
		const ids = letterIds.split(' ').filter(Boolean);
		let frame = 0;
		const measure = () => {
			frame = 0;
			const line = (controlsEl?.getBoundingClientRect().bottom ?? 0) + 24;
			let current = ids[0] ?? '';
			for (const id of ids) {
				const top = document.getElementById(id)?.getBoundingClientRect().top;
				if (top !== undefined && top <= line) current = id;
			}
			active = current;
		};
		const onScroll = () => (frame ||= requestAnimationFrame(measure));
		measure();
		window.addEventListener('scroll', onScroll, { passive: true });
		return () => {
			window.removeEventListener('scroll', onScroll);
			cancelAnimationFrame(frame);
		};
	});
	// On a phone the rail is one row that scrolls sideways — keep the lit
	// letter in it on screen as you scroll down the page.
	$effect(() => {
		const link = active && railEl?.querySelector<HTMLElement>(`a[href="#${active}"]`);
		if (!railEl || !link || railEl.scrollWidth <= railEl.clientWidth) return;
		const left = link.offsetLeft - railEl.offsetLeft;
		if (left < railEl.scrollLeft || left + link.offsetWidth > railEl.scrollLeft + railEl.clientWidth)
			railEl.scrollTo({ left: left - railEl.clientWidth / 2, behavior: 'instant' });
	});

	const title = $derived(t('nav.azIndex'));
	const hreflang = hreflangAll('/authors/');
	const canonical = `${SITE_URL}${localizeHref('/authors')}`;
	const authorsLd = $derived(
		itemList(
			title,
			groups.flatMap((g) =>
				g.entries.map((e) => ({ name: e.author.name, url: localizeHref(`/authors/${e.author.slug}`) }))
			)
		)
	);
</script>

<Seo
	title={`${t('authors.metaTitle')} — Ochorus`}
	description={t('authors.indexTagline')}
	{canonical}
	{hreflang}
	ogImage={`${SITE_URL}/og/biographies.png`}
	structuredData={groups.length ? [authorsLd] : []}
/>

{#snippet clearAction()}
	<button class="btn btn-ghost" onclick={clearFilters}>{t('common.clearFilters')}</button>
{/snippet}

<div class="page-col px-5 py-10" style="--pinned-offset: calc(var(--appnav-h, 0px) + {pinnedH}px)">
	<PageHeader {title} tagline={t('authors.indexTagline')} meta={groups.length ? counts : undefined} />
	<!-- The library's people in this language (`countWriters`, the home page's
	     number), not the rows below: the rows are the English roster off
	     English, and "James DeGreef and Ochorus" — an imprint, not a person —
	     keeps a row so its series stays indexed. No book count: the Originals
	     live on /originals, so any count here fell short of the library's. -->
	{#snippet counts()}
		{i18n.count(data.people, 'common.authorOne', 'common.authorMany')}
	{/snippet}
	<!-- The library tabs sit under the title, as on /books (design review #4). -->
	<LibraryTabs current="az" />

	<!-- Empty only when the fetch failed (the build throws instead; see +page.ts). -->
	{#if data.loadError || groups.length === 0}
		<EmptyState message={t('common.loadError')} onRetry />
	{:else}
		<AuthorsFaceWall {faces} />

		<!-- The other index of the same writers: their lives, by era, tradition
		     and place. -->
		<p class="mb-6 text-small">
			<a href={localizeHref('/biographies')}>{t('authors.biosLink')} <Arrow /></a>
		</p>

		{#if meet.length}
			<section class="mb-10" aria-labelledby="meet-first">
				<h2 id="meet-first" class="section-label">{t('authors.meetFirst')}</h2>
				<p class="-mt-1 mb-4 max-w-prose text-small text-muted">{t('authors.meetNote')}</p>
				<ul class="meet">
					{#each meet as m (m.author.slug)}
						{@const life = formatLifespan(m.author.birth_year, m.author.death_year, t('common.bornPrefix'))}
						<li class="meet-card card-lift">
							<Portrait
								slug={m.author.slug}
								name={m.author.name}
								url={m.author.photo_url}
								px={56}
								decorative
								class="h-14 w-14 shrink-0"
							/>
							<div class="min-w-0">
								<a class="meet-name font-display font-semibold" href={localizeHref(`/authors/${m.author.slug}`)}
									>{m.author.name}</a
								>
								{#if life}<p class="text-small text-muted">{life}</p>{/if}
								<a class="mt-1 block text-small font-semibold" href={localizeHref(`/books/${m.book.slug}`)}
									>{t('authors.startWith').replace('%title%', m.book.title)} <Arrow /></a
								>
							</div>
						</li>
					{/each}
				</ul>
			</section>
		{/if}

		<!-- The timeline: each era a column on one ruled line, its pictured
		     writers earliest-born first, and the era's page for the rest. A row
		     that scrolls sideways on a phone, like a timeline should. -->
		{#if eras.length > 1}
			<section class="mb-10" aria-labelledby="timeline">
				<h2 id="timeline" class="section-label">{t('authors.timeline')}</h2>
				<p class="-mt-1 mb-4 max-w-prose text-small text-muted">{t('authors.timelineNote')}</p>
				<ol class="timeline" use:scrollEdges>
					{#each eras as row (row.era.id)}
						<li class="era" style="--era-hue: {ERA_HUE[row.era.id]}">
							<a class="era-head" href={localizeHref(`/biographies/era/${row.era.id}`)}>
								<span class="era-name font-display">{t(row.era.k)}</span>
								<span class="era-range">{row.era.range}</span>
							</a>
							<ul class="era-faces">
								{#each row.faces as f (f.slug)}
									<li>
										<a href={localizeHref(`/authors/${f.slug}`)} title={f.name} class="face block">
											<Portrait slug={f.slug} name={f.name} url={f.photo_url} px={40} tone="hover" class="h-10 w-10" />
										</a>
									</li>
								{/each}
							</ul>
							{#if row.more}
								<a class="mt-2 inline-block text-small text-muted" href={localizeHref(`/biographies/era/${row.era.id}`)}
									>{t('authors.timelineMore').replace('%n%', String(row.more))}</a
								>
							{/if}
						</li>
					{/each}
				</ol>
			</section>
		{/if}

		<!-- Traditions and regions, above the pinned bar rather than in it: two
		     wrapped rows of chips would have followed the reader down the page. -->
		{#if data.hubs.length}
			<div class="chip-scroller mb-4" role="group" aria-label={t('authors.byTradition')}>
				{#each data.hubs as h (h.slug)}
					<button
						type="button"
						class="chip"
						class:active={hub === h.slug}
						aria-pressed={hub === h.slug}
						onclick={() => (hub = hub === h.slug ? null : h.slug)}>{h.label}</button
					>
				{/each}
			</div>
		{/if}

		<!-- Filter + A–Z, pinned under the app nav — the Biographies controls bar.
		     At one column on a phone this page is ~25 screens long, so the letter
		     jump has to come WITH you. Its height is measured (the rail wraps),
		     and --pinned-offset above lands every jump below it. -->
		<FilterBar bind:pinned={pinnedH} bind:el={controlsEl} class="mb-8">
			<div class="filter-row">
				<input
					bind:value={query}
					type="search"
					class="filter-field grow"
					placeholder={t('books.filterPlaceholder')}
					aria-label={t('books.filterPlaceholder')}
				/>
			</div>
			{#if filtering}
				<FilterSummary
					shown={shownWriters}
					total={writerCount}
					template={t('bios.showing')}
					onClear={clearFilters}
					class="mt-1.5"
				/>
			{/if}
			<!-- Real anchors, not the Biographies rail's buttons: every group is in
			     the HTML (no paging), so each #letter- target always exists. On a
			     phone one row that swipes sideways; from sm up it wraps. -->
			<AzRail
				bind:el={railEl}
				class="mt-1.5"
				letters={rail}
				present={(l) => present.has(l)}
				active={activeLetter}
				href={(l) => `#${anchor(l)}`}
				label={t('bios.jumpAz')}
			/>
		</FilterBar>

		{#if listedGroups.length === 0}
			<EmptyState art="search" message={t('bios.noResults')} action={clearAction} />
		{/if}

		{#each listedGroups as g (g.letter)}
			<section id={anchor(g.letter)} class="az-group mb-10">
				<GroupHeading name={g.letter} count={g.entries.length} />
				<!-- Columns, not a grid: a grid row is as tall as its longest writer,
				     so one long list left blank cells beside it. Each writer flows
				     straight under the one above, reading down then across. -->
				<ul class="gap-x-10 sm:columns-2 lg:columns-3">
					{#each g.entries as entry ('author' in entry ? entry.author.slug : ' bible')}
						{#if !('author' in entry)}
							<!-- The Bible's pinned entry: the hub, and how many books it holds. -->
							<li class="mb-5 flex break-inside-avoid gap-3">
								<span class="emblem-chip" style="--chip-size: 2rem; --chip-hue: var(--section-bible)" aria-hidden="true"
									><img src="/marks/emblem-bible.svg" alt="" width="21" height="21" /></span
								>
								<div class="min-w-0 flex-1">
									<a class="font-semibold hover:text-accent" href={localizeHref(BIBLE_PATH)}>{entry.name}</a>
									<span class="text-small text-muted">
										· {i18n.count(entry.count, 'common.bookOne', 'common.bookMany')}</span
									>
								</div>
							</li>
						{:else}
						{@const { author, rows } = entry}
						{@const life = formatLifespan(author.birth_year, author.death_year, t('common.bornPrefix'))}
						{@const collapsed = collapses(author.slug, rows.length)}
						{@const w = data.works[author.slug]}
						<!-- The portrait sits beside the entry, not in the column's flow:
						     the li stays one unbroken block (break-inside-avoid). The
						     GroupHeading 32px recipe, greyed like the Biographies roster;
						     alt="" because the name link beside it already says who. A
						     writer added from a book has a photo_url too (the book's author
						     carries one) — blank means no free image: initials instead. -->
						<li class="mb-5 flex break-inside-avoid gap-3">
							<Portrait
								slug={author.slug}
								name={author.name}
								url={author.photo_url}
								px={32}
								decorative
								class="h-8 w-8"
								initialsClass="text-micro"
							/>
							<div class="min-w-0 flex-1">
								<a class="font-semibold hover:text-accent" href={localizeHref(`/authors/${author.slug}`)}
									>{author.name}</a
								>
								{#if life}<span class="text-small text-muted"> · {life}</span>{/if}
								{#if rows.length}
									<ul id="books-{author.slug}" class="az-books mt-1 space-y-0.5 text-small">
										{#each rows as { book: b, editions }, i (b.slug)}
											<li hidden={collapsed && i >= ROWS_SHOWN}>
												<a class="text-muted hover:text-accent" href={localizeHref(`/books/${b.slug}`)}
													>{b.title}</a
												>
												<!-- Young-reader editions ride their full text as chips. The
												     chip reads the audience from the edition's own (already
												     translated) title, so no UI string is needed. -->
												{#each editions as { book: ed, audience } (ed.slug)}
													<a
														class="tag tag-sm ms-1.5"
														href={localizeHref(`/books/${ed.slug}`)}
														aria-label={ed.title}
														title={ed.title}>{audience}</a
													>
												{/each}
											</li>
										{/each}
									</ul>
									{#if collapsible(rows.length)}
										<button
											type="button"
											class="mt-1 text-small font-semibold text-accent hover:underline"
											aria-expanded={!collapsed}
											aria-controls="books-{author.slug}"
											onclick={(e) => toggle(author.slug, e.currentTarget)}
										>
											{collapsed
												? t('bios.showMore').replace('%n%', String(rows.length - ROWS_SHOWN))
												: t('search.showLess')}
										</button>
									{/if}
								{/if}
								<!-- What else this writer has in this language. Sermons always
								     (Maclaren has seven and no book — without this his entry
								     looked broken). Quotations when a person has approved some
								     (English only — see +page.ts). The biography only for a writer
								     with nothing else listed: almost everyone has one, and on every
								     entry the link would be noise — the name already leads there. -->
								{#if w?.sermons || w?.quotes || (w?.bio && !rows.length)}
									<div class="mt-1 flex flex-wrap gap-x-3 text-small">
										{#if w.sermons}
											<a
												class="inline-flex items-center gap-1 text-muted hover:text-accent"
												href={localizeHref(`/authors/${author.slug}#sermons`)}
												><Icon name="mic" size={14} />{i18n.count(w.sermons, 'common.sermonOne', 'common.sermonMany')}</a
											>
										{/if}
										{#if w.quotes}
											<!-- Un-localized, like the author page's Quotes button: the
											     quote pages exist in English only. -->
											<a
												class="inline-flex items-center gap-1 text-muted hover:text-accent"
												href={`/quotes/${author.slug}/`}
												><Icon name="quote" size={14} />{(i18n.tn(w.quotes, 'quotes.countOne', 'quotes.countMany')
												).replace('%count%', String(w.quotes))}</a
											>
										{/if}
										{#if !w.sermons && !w.quotes}
											<a
												class="inline-flex items-center gap-1 text-muted hover:text-accent"
												href={localizeHref(`/authors/${author.slug}#bio`)}
												><Icon name="users" size={14} />{t('articles.kindBiography')}</a
											>
										{/if}
									</div>
								{/if}
							</div>
						</li>
						{/if}
					{/each}
				</ul>
			</section>
		{/each}

		<!-- Browse by era — at the foot, as on Biographies, not above the list as
		     a second filter row. Load-bearing for the build: this page is the
		     prerender's seed for every localized era page (see +page.ts). -->
		{#if data.eras.length}
			<nav class="mt-14 border-t border-border pt-8" aria-label={t('hubs.byEra')}>
				<h2 class="section-label mb-2.5">{t('hubs.byEra')}</h2>
				<ul class="flex flex-wrap gap-2">
					{#each data.eras as era (era.id)}
						<li><a class="tag" href={localizeHref(`/biographies/era/${era.id}`)}>{t(era.k)}</a></li>
					{/each}
				</ul>
			</nav>
		{/if}
	{/if}
</div>

<style>
	.meet {
		display: grid;
		gap: 0.75rem;
	}
	@media (min-width: 640px) {
		.meet {
			grid-template-columns: repeat(2, minmax(0, 1fr));
		}
	}
	@media (min-width: 1024px) {
		.meet {
			grid-template-columns: repeat(4, minmax(0, 1fr));
		}
	}
	.meet-card {
		display: flex;
		gap: 0.875rem;
		align-items: flex-start;
		padding: 1rem;
		border: 1px solid var(--color-border);
		border-radius: var(--radius-card);
		background: var(--color-surface);
	}
	.meet-name {
		color: var(--color-text);
		font-size: var(--fs-h3);
		line-height: 1.2;
	}
	.meet-name:hover {
		color: var(--color-accent);
	}
	/* One ruled line through the era heads; each era wears its own hue. */
	.timeline {
		display: grid;
		grid-auto-flow: column;
		grid-auto-columns: minmax(10.5rem, 1fr);
		gap: 1rem;
		overflow-x: auto;
		padding-block-end: 0.5rem;
		list-style: none;
		margin: 0;
		padding-inline: 0;
	}
	.era-head {
		display: block;
		padding-block: 0.5rem 0.6rem;
		border-block-start: 4px solid var(--era-hue);
		color: var(--color-text);
		text-decoration: none;
	}
	.era-head:hover .era-name {
		color: var(--color-accent);
	}
	.era-name {
		display: block;
		font-weight: 600;
		line-height: 1.2;
	}
	.era-range {
		font-size: var(--fs-small);
		color: var(--color-muted);
		font-variant-numeric: tabular-nums;
	}
	.era-faces {
		display: flex;
		flex-wrap: wrap;
		gap: 0.375rem;
		list-style: none;
		margin: 0;
		padding: 0;
	}
	.face {
		border-radius: var(--radius-pill);
		transition: transform var(--duration-base);
	}
	.face:hover,
	.face:focus-visible {
		transform: scale(1.12);
	}
	@media (prefers-reduced-motion: reduce) {
		.face {
			transition: none;
		}
	}

	/* Jumps land the letter heading below the app nav AND the pinned controls. */
	.az-group {
		scroll-margin-top: calc(var(--pinned-offset, var(--appnav-h, 0px)) + 1rem);
	}
	/* A writer's titles were 18px rows 2px apart — a finger took the next one.
	   On touch each title is a 24px target, the minimum with nothing crowding it. */
	@media (pointer: coarse) {
		.az-books > li > a:first-child {
			display: inline-block;
			min-height: 1.5rem;
			padding-block: 0.15rem;
		}
	}
</style>
