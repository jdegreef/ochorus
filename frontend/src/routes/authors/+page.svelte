<script lang="ts">
	import { formatLifespan } from '$lib/library-public';
	import { SITE_URL } from '$lib/config';
	import { localizeHref } from '$lib/href';
	import { i18n } from '$lib/i18n.svelte';
	import { lang } from '$lib/lang.svelte';
	import { hreflangAll, itemList } from '$lib/seo';
	import { authorIndex, filterIndex, indexRows } from '$lib/authorIndex';
	import { SvelteSet } from 'svelte/reactivity';
	import { tick } from 'svelte';
	import { ORIGINALS_SLUG } from '$lib/originals';
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

	// The library A–Z: every writer and, under each, every book of theirs in
	// this language — see $lib/authorIndex for why this page exists. It used to
	// be a hidden, noindexed crawl anchor that redirected to /biographies on
	// mount; the same complete link set is now the page itself, visible and
	// indexable. Deliberately NOT paginated: it must stay complete, for readers
	// and for the prerender crawl (svelte.config.js seeds it per locale).
	let { data }: { data: PageData } = $props();
	const t = i18n.t;

	// The imprint is not a person and has no author page — /originals instead.
	const groups = $derived(authorIndex(data.authors, data.books, lang.current, [ORIGINALS_SLUG]));
	const rowGroups = $derived(indexRows(groups));
	const writerCount = $derived(groups.reduce((n, g) => n + g.entries.length, 0));
	const bookCount = $derived(groups.reduce((n, g) => n + g.entries.reduce((m, e) => m + e.books.length, 0), 0));

	// The filter only narrows what is SHOWN, after hydration: the prerendered
	// HTML is always the full, unfiltered index (the query starts blank).
	let query = $state('');
	const shownGroups = $derived(filterIndex(rowGroups, query));
	const filtering = $derived(query.trim() !== '');
	const shownWriters = $derived(shownGroups.reduce((n, g) => n + g.entries.length, 0));

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
	const present = $derived(new Set(shownGroups.map((g) => g.letter)));
	const rail = $derived(present.has('#') ? [...AZ, '#'] : AZ);
	// Joined so the effect below re-binds only when the SET of letters changes,
	// not on every keystroke that rebuilds `shownGroups`.
	const letterIds = $derived(shownGroups.map((g) => anchor(g.letter)).join(' '));

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
	title={`${title} — Ochorus`}
	description={t('authors.indexTagline')}
	{canonical}
	{hreflang}
	ogImage={`${SITE_URL}/og/biographies.png`}
	structuredData={groups.length ? [authorsLd] : []}
/>

{#snippet clearAction()}
	<button class="btn btn-ghost" onclick={() => (query = '')}>{t('common.clearFilters')}</button>
{/snippet}

<div class="page-col px-5 py-10" style="--pinned-offset: calc(var(--appnav-h, 0px) + {pinnedH}px)">
	<LibraryTabs current="az" />
	<PageHeader {title} tagline={t('authors.indexTagline')} meta={groups.length ? counts : undefined} />
	{#snippet counts()}
		{writerCount}
		{writerCount === 1 ? t('common.authorOne') : t('common.authorMany')}
		<span class="opacity-50">·</span>
		{bookCount}
		{bookCount === 1 ? t('common.bookOne') : t('common.bookMany')}
	{/snippet}

	<!-- Empty only when the fetch failed (the build throws instead; see +page.ts). -->
	{#if data.loadError || groups.length === 0}
		<EmptyState message={t('common.loadError')} onRetry />
	{:else}
		<!-- The other index of the same writers: their lives, by era, tradition
		     and place. -->
		<p class="mb-6 text-small">
			<a href={localizeHref('/biographies')}>{t('authors.biosLink')} <Arrow /></a>
		</p>

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
					onClear={() => (query = '')}
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

		{#if shownGroups.length === 0}
			<EmptyState art="search" message={t('bios.noResults')} action={clearAction} />
		{/if}

		{#each shownGroups as g (g.letter)}
			<section id={anchor(g.letter)} class="az-group mb-10">
				<GroupHeading name={g.letter} count={g.entries.length} />
				<!-- Columns, not a grid: a grid row is as tall as its longest writer,
				     so one long list left blank cells beside it. Each writer flows
				     straight under the one above, reading down then across. -->
				<ul class="gap-x-10 sm:columns-2 lg:columns-3">
					{#each g.entries as { author, rows } (author.slug)}
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
									<ul id="books-{author.slug}" class="mt-1 space-y-0.5 text-small">
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
												><Icon name="mic" size={14} />{w.sermons}
												{w.sermons === 1 ? t('common.sermonOne') : t('common.sermonMany')}</a
											>
										{/if}
										{#if w.quotes}
											<!-- Un-localized, like the author page's Quotes button: the
											     quote pages exist in English only. -->
											<a
												class="inline-flex items-center gap-1 text-muted hover:text-accent"
												href={`/quotes/${author.slug}/`}
												><Icon name="quote" size={14} />{(w.quotes === 1
													? t('quotes.countOne')
													: t('quotes.countMany')
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
	/* Jumps land the letter heading below the app nav AND the pinned controls. */
	.az-group {
		scroll-margin-top: calc(var(--pinned-offset, var(--appnav-h, 0px)) + 1rem);
	}
</style>
