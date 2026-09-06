<script lang="ts">
	import { onMount } from 'svelte';
	import {
		listAuthors,
		listBooks,
		listPlans,
		listSermons,
		type AuthorBio,
		type BookSummary,
		type PlanSummary,
		type SermonSummary
	} from '$lib/library-public';
	import { favorites, type FavoriteEntry } from '$lib/favorites.svelte';
	import { planProgress } from '$lib/planProgress.svelte';
	import { getLang } from '$lib/lang.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { unslug } from '$lib/strings';
	import PageHeader from '$lib/components/PageHeader.svelte';
	import SectionHeader from '$lib/components/SectionHeader.svelte';
	import LibraryBookCard from '$lib/components/LibraryBookCard.svelte';
	import AuthorTile from '$lib/components/AuthorTile.svelte';
	import SermonCard from '$lib/components/SermonCard.svelte';
	import CoverStrip from '$lib/components/CoverStrip.svelte';
	import ProgressBar from '$lib/components/ProgressBar.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';

	/**
	 * "My Library" — the reader's saved books, followed authors, saved plans and
	 * sermons, as covers with reading progress, not the bare text pills the old
	 * homepage shelf showed. Client-only and personal (favorites are device-local
	 * first, synced when signed in), so it works signed-out too and never
	 * prerenders.
	 *
	 * Titles/covers resolve from the public catalogs in the current language; a
	 * favorite whose work has no row in that language can't be drawn as a cover,
	 * so it falls back to a slug-derived pill (the old shelf's behaviour) rather
	 * than vanishing.
	 */
	const t = i18n.t;

	// Resolved catalogs, keyed by slug. Populated on mount; empty until then.
	let books = $state<Record<string, BookSummary>>({});
	let authors = $state<Record<string, AuthorBio>>({});
	let plans = $state<Record<string, PlanSummary>>({});
	let sermons = $state<Record<string, SermonSummary>>({});
	let loaded = $state(false);

	onMount(async () => {
		const lang = getLang();
		const [a, b, p, s] = await Promise.all([
			listAuthors(lang).catch(() => [] as AuthorBio[]),
			listBooks(lang).catch(() => [] as BookSummary[]),
			listPlans(lang).catch(() => [] as PlanSummary[]),
			listSermons(lang).catch(() => [] as SermonSummary[])
		]);
		authors = Object.fromEntries(a.map((x) => [x.slug, x]));
		books = Object.fromEntries(b.map((x) => [x.slug, x]));
		plans = Object.fromEntries(p.map((x) => [x.slug, x]));
		sermons = Object.fromEntries(s.map((x) => [x.slug, x]));
		loaded = true;
	});

	// favorites.all() is reactive (favorites.ticks), so un-hearting a work on its
	// own page and coming back reflects immediately.
	const entriesOf = (kind: FavoriteEntry['kind']) =>
		favorites.all().filter((e) => e.kind === kind);

	const bookFavs = $derived(entriesOf('book'));
	const authorFavs = $derived(entriesOf('author'));
	const planFavs = $derived(entriesOf('plan'));
	const sermonFavs = $derived(entriesOf('sermon'));
	const isEmpty = $derived(
		bookFavs.length + authorFavs.length + planFavs.length + sermonFavs.length === 0
	);

	const HREF: Record<FavoriteEntry['kind'], (slug: string) => string> = {
		author: (s) => `/authors/${s}`,
		book: (s) => `/books/${s}`,
		plan: (s) => `/plans/${s}`,
		sermon: (s) => `/sermons/${s}`
	};

	const planPercent = (plan: PlanSummary) =>
		plan.day_count > 0
			? Math.min(100, Math.round((planProgress.doneDays(plan.slug).length / plan.day_count) * 100))
			: 0;
</script>

<svelte:head>
	<title>{t('fav.yourFavorites')} — Ochorus</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<div class="page-col px-5 py-10">
	<PageHeader title={t('fav.yourFavorites')} />

	{#if loaded && isEmpty}
		<EmptyState message={t('fav.empty')}>
			{#snippet action()}
				<a href={localizeHref('/books')} class="btn btn-primary hover:no-underline"
					>{t('home.browseLibrary')}</a
				>
			{/snippet}
		</EmptyState>
	{/if}

	<!-- A saved favorite whose work has no row in the current language can't draw
	     a cover; it falls back to this pill so it is never silently lost. -->
	{#snippet fallbackPills(entries: FavoriteEntry[], resolved: Record<string, unknown>)}
		{@const missing = entries.filter((e) => !resolved[e.slug])}
		<!-- Only once the catalogs are in: before that every entry is "unresolved",
		     which would flash the whole shelf as pills and then swap to covers. -->
		{#if loaded && missing.length}
			<div class="mt-3 flex flex-wrap gap-2">
				{#each missing as e (e.slug)}
					<a
						href={localizeHref(HREF[e.kind](e.slug))}
						class="tag"
					>
						♥ {unslug(e.slug)}
					</a>
				{/each}
			</div>
		{/if}
	{/snippet}

	<!-- Books — the centrepiece: covers with the reader's own progress -->
	{#if bookFavs.length}
		<section class="pt-8">
			<SectionHeader title={t('fav.groupBooks')} />
			<div class="grid grid-cols-2 gap-x-4 gap-y-6 sm:grid-cols-3 lg:grid-cols-5">
				{#each bookFavs as e (e.slug)}
					{#if books[e.slug]}
						<LibraryBookCard book={books[e.slug]} />
					{/if}
				{/each}
			</div>
			{@render fallbackPills(bookFavs, books)}
		</section>
	{/if}

	<!-- Following: hearted authors -->
	{#if authorFavs.length}
		<section class="pt-10">
			<SectionHeader title={t('fav.groupAuthors')} />
			<div class="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
				{#each authorFavs as e (e.slug)}
					{#if authors[e.slug]}
						<AuthorTile author={authors[e.slug]} />
					{/if}
				{/each}
			</div>
			{@render fallbackPills(authorFavs, authors)}
		</section>
	{/if}

	<!-- Saved reading plans -->
	{#if planFavs.length}
		<section class="pt-10">
			<SectionHeader title={t('fav.groupPlans')} />
			<div class="grid gap-4 sm:grid-cols-2">
				{#each planFavs as e (e.slug)}
					{#if plans[e.slug]}
						{@const plan = plans[e.slug]}
						{@const pct = planPercent(plan)}
						<a
							href={localizeHref(`/plans/${plan.slug}`)}
							class="flex flex-col gap-3 rounded-card border border-border p-4 hover:bg-surface-2 hover:no-underline"
						>
							<div class="flex items-start justify-between gap-3">
								<span class="min-w-0">
									<span class="block text-body font-semibold text-text">{plan.title}</span>
									<span class="block text-small text-muted">
										{plan.day_count}
										{t('plans.days')}
									</span>
								</span>
								<CoverStrip covers={plan.covers} max={3} />
							</div>
							{#if pct > 0}
								<div>
									<ProgressBar percent={pct} label="{plan.title}: {t('plans.complete')}" />
									<div class="mt-1 text-eyebrow text-muted">{pct}% {t('plans.complete')}</div>
								</div>
							{/if}
						</a>
					{/if}
				{/each}
			</div>
			{@render fallbackPills(planFavs, plans)}
		</section>
	{/if}

	<!-- Saved sermons -->
	{#if sermonFavs.length}
		<section class="pt-10 pb-4">
			<SectionHeader title={t('fav.groupSermons')} />
			<div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
				{#each sermonFavs as e (e.slug)}
					{#if sermons[e.slug]}
						<SermonCard sermon={sermons[e.slug]} showAuthor />
					{/if}
				{/each}
			</div>
			{@render fallbackPills(sermonFavs, sermons)}
		</section>
	{/if}
</div>
