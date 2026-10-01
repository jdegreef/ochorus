<script lang="ts">
	import { formatLifespan } from '$lib/library-public';
	import { SITE_URL } from '$lib/config';
	import { localizeHref } from '$lib/href';
	import { i18n } from '$lib/i18n.svelte';
	import { lang } from '$lib/lang.svelte';
	import { hreflangAll, itemList } from '$lib/seo';
	import { authorIndex, filterIndex, indexRows } from '$lib/authorIndex';
	import { splitEdition } from '$lib/edition';
	import { scrollSpy } from '$lib/scrollSpy.svelte';
	import { SvelteSet } from 'svelte/reactivity';
	import { ORIGINALS_SLUG } from '$lib/originals';
	import type { PageData } from './$types';
	import Seo from '$lib/components/Seo.svelte';
	import PageHeader from '$lib/components/PageHeader.svelte';
	import GroupHeading from '$lib/components/GroupHeading.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import FilterSummary from '$lib/components/FilterSummary.svelte';

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
	const collapses = (slug: string, rows: number) => !filtering && rows > ROWS_SHOWN + 1 && !expanded.has(slug);
	function toggle(slug: string) {
		if (expanded.has(slug)) expanded.delete(slug);
		else expanded.add(slug);
	}

	// The A–Z rail is the full alphabet, so its shape doesn't change with the
	// language or the filter; letters with nobody under them are dimmed.
	const AZ = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('');
	const anchor = (letter: string) => `letter-${letter === '#' ? 'other' : letter}`;
	const present = $derived(new Set(shownGroups.map((g) => g.letter)));
	const rail = $derived(present.has('#') ? [...AZ, '#'] : AZ);
	// A thin band just under the pinned bar (~15–20% down), not scrollSpy's
	// mid-screen default: a short letter (M: four names) that a jump lands at
	// the top would otherwise never reach the middle, and the rail lit the next.
	const spy = scrollSpy(() => shownGroups.map((g) => anchor(g.letter)), { rootMargin: '-22% 0px -77% 0px' });

	/** Measured height of the pinned controls bar — jumps land below it. */
	let controlsH = $state(0);

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

<div class="page-col px-5 py-10" style="--pinned-offset: calc(var(--appnav-h, 0px) + {controlsH}px)">
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
		{#if data.eras.length}
			<nav class="mb-6 flex flex-wrap items-center gap-2" aria-label={t('bios.sortEra')}>
				<span class="eyebrow me-1">{t('bios.sortEra')}</span>
				{#each data.eras as era (era.id)}
					<a class="tag" href={localizeHref(`/biographies/era/${era.id}`)}>{t(era.k)}</a>
				{/each}
			</nav>
		{/if}

		<!-- Filter + A–Z, pinned under the app nav — the Biographies controls bar.
		     At one column on a phone this page is ~25 screens long, so the letter
		     jump has to come WITH you. Its height is measured (the rail wraps),
		     and --pinned-offset above lands every jump below it. -->
		<div
			bind:clientHeight={controlsH}
			class="sticky z-20 -mx-5 mb-8 border-b border-border bg-bg px-5 pb-2.5 pt-3"
			style="top: var(--appnav-h, 0px)"
		>
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
			<nav
				class="mt-1.5 flex gap-x-1 gap-y-0.5 overflow-x-auto text-small [scrollbar-width:none] sm:flex-wrap sm:overflow-visible"
				aria-label={t('bios.jumpAz')}
			>
				{#each rail as letter (letter)}
					{#if present.has(letter)}
						<a
							href="#{anchor(letter)}"
							class="shrink-0 rounded-sm px-1.5 py-0.5 font-semibold text-accent hover:bg-accent-soft"
							class:az-current={spy.active === anchor(letter)}
							aria-current={spy.active === anchor(letter) ? 'location' : undefined}
							onclick={() => spy.set(anchor(letter))}>{letter}</a
						>
					{:else}
						<span class="shrink-0 px-1.5 py-0.5 text-muted opacity-40" aria-hidden="true">{letter}</span>
					{/if}
				{/each}
			</nav>
		</div>

		{#if shownGroups.length === 0}
			<EmptyState message={t('bios.noResults')} action={clearAction} />
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
						<li class="mb-5 break-inside-avoid">
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
											{#each editions as ed (ed.slug)}
												<a
													class="edition-chip ms-1.5"
													href={localizeHref(`/books/${ed.slug}`)}
													aria-label={ed.title}
													title={ed.title}>{splitEdition(ed.slug, ed.title)?.audience ?? ed.title}</a
												>
											{/each}
										</li>
									{/each}
								</ul>
								{#if rows.length > ROWS_SHOWN + 1 && !filtering}
									<button
										type="button"
										class="mt-1 text-small font-semibold text-accent hover:underline"
										aria-expanded={!collapsed}
										aria-controls="books-{author.slug}"
										onclick={() => toggle(author.slug)}
									>
										{collapsed
											? t('bios.showMore').replace('%n%', String(rows.length - ROWS_SHOWN))
											: t('search.showLess')}
									</button>
								{/if}
							{/if}
						</li>
					{/each}
				</ul>
			</section>
		{/each}
	{/if}
</div>

<style>
	/* Jumps land the letter heading below the app nav AND the pinned controls. */
	.az-group {
		scroll-margin-top: calc(var(--pinned-offset, var(--appnav-h, 0px)) + 1rem);
	}
	/* The letter you are scrolled into, lit on the rail. */
	.az-current {
		background: var(--accent);
		color: var(--accent-contrast);
	}
	.edition-chip {
		display: inline-block;
		border: 1px solid var(--accent-soft-border);
		border-radius: 9999px;
		background: var(--accent-soft);
		padding: 0 0.45rem;
		font-size: var(--fs-micro);
		font-weight: 600;
		line-height: 1.5;
		color: var(--accent);
		white-space: nowrap;
	}
	.edition-chip:hover {
		border-color: var(--accent);
	}
</style>
