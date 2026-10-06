<script lang="ts">
	import { onMount } from 'svelte';
	import {
		listBooks,
		listSermons,
		listPlans,
		type BookSummary,
		type SermonSummary,
		type PlanSummary
	} from '$lib/library-public';
	import { buildResumeItems, type ResumeItem } from '$lib/resumeItems';
	import { buildPlanRows, type PlanRow } from '$lib/planRows';
	import { getLang } from '$lib/lang.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import PageHeader from '$lib/components/PageHeader.svelte';
	import SectionHeader from '$lib/components/SectionHeader.svelte';
	import WorkCard from '$lib/components/WorkCard.svelte';
	import PlanCard from '$lib/components/PlanCard.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';

	/**
	 * "Reading" — everything the reader has started, split into what's still in
	 * progress and what they've finished. The dashboard's two reading tiles
	 * ("In progress", "Finished") point here; it's also the full-list home the
	 * capped "Continue reading" strip never had.
	 *
	 * Client-only and personal (progress is device-local, kept in step with the
	 * account by the sign-in sync), so it works signed-out too and never
	 * prerenders. Titles/covers resolve from the current-language catalogs; a
	 * work with no row in that language is dropped rather than shown as a slug,
	 * exactly as on the strip.
	 */
	const t = i18n.t;

	let books = $state<BookSummary[]>([]);
	let sermons = $state<SermonSummary[]>([]);
	let plans = $state<PlanSummary[]>([]);
	let loaded = $state(false);
	// localStorage is read on mount; an account sync landing after navigation
	// re-reads via the ochorus:sync event, like the dashboard blocks.
	let ticks = $state(0);

	onMount(() => {
		const bump = () => ticks++;
		window.addEventListener('ochorus:sync', bump);
		const lang = getLang();
		// A failed catalog fetch degrades to an empty list — the same offline
		// tolerance the strip has; nothing here rejects.
		Promise.all([
			listBooks(lang).catch(() => [] as BookSummary[]),
			listSermons(lang).catch(() => [] as SermonSummary[]),
			listPlans(lang).catch(() => [] as PlanSummary[])
		]).then(([b, s, p]) => {
			books = b;
			sermons = s;
			plans = p;
			loaded = true;
		});
		return () => window.removeEventListener('ochorus:sync', bump);
	});

	// The split both dashboard tiles link to: "In progress" is everything still
	// being read; "Finished" everything completed — for works, the stored
	// finished_at stamp (reaching the end, or marking it done). Reading plans join
	// the same split (a plan with no next day is finished), so this is the one
	// home for "what I've read", works and plans alike.
	// `items` needs `void ticks` because works-progress (localStorage) isn't
	// rune-reactive; `buildPlanRows` already reads planProgress.ticks (bumped on
	// mutations and on ochorus:sync), so plan rows refresh without it.
	const items = $derived.by(() => {
		void ticks;
		return buildResumeItems(books, sermons);
	});
	const planRows = $derived(buildPlanRows(plans));
	const inProgress = $derived(items.filter((i) => !i.finished));
	const finished = $derived(items.filter((i) => i.finished));
	const plansInProgress = $derived(planRows.filter((r) => !r.finished));
	const plansFinished = $derived(planRows.filter((r) => r.finished));
	const isEmpty = $derived(loaded && items.length === 0 && planRows.length === 0);
</script>

<svelte:head>
	<title>{t('settings.navReading')} — Ochorus</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<div class="page-col px-5 py-10">
	<PageHeader title={t('settings.navReading')} tagline={t('reading.subtitle')} />

	{#if isEmpty}
		<EmptyState message={t('reading.empty')}>
			{#snippet action()}
				<a href={localizeHref('/books')} class="btn btn-primary hover:no-underline"
					>{t('home.browseLibrary')}</a
				>
			{/snippet}
		</EmptyState>
	{/if}

	<!-- One section body for both "In progress" and "Finished": works then plans
	     in ONE grid, so a lone work and a lone plan sit side by side rather than
	     as two stacked single-item rows. `complete` is WorkCard's finished variant
	     (drops the meter for a completion line). -->
	{#snippet cards(works: ResumeItem[], plansList: PlanRow[], complete: boolean)}
		<div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
			{#each works as item (item.key)}
				<WorkCard {item} {complete} />
			{/each}
			{#each plansList as r (r.slug)}
				<PlanCard row={r} />
			{/each}
		</div>
	{/snippet}

	{#if inProgress.length || plansInProgress.length}
		<section class="pt-2">
			<SectionHeader title={t('settings.statInProgress')} />
			{@render cards(inProgress, plansInProgress, false)}
		</section>
	{/if}

	{#if finished.length || plansFinished.length}
		<!-- The Finished tile deep-links to #finished; the offset clears the sticky
		     header so the heading isn't hidden under it on arrival. -->
		<section id="finished" class="scroll-mt-24 pt-10">
			<SectionHeader title={t('settings.statFinished')} />
			{@render cards(finished, plansFinished, true)}
		</section>
	{/if}
</div>
