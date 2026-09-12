<script lang="ts">
	import { onMount } from 'svelte';
	import { listBooks, listSermons, type BookSummary, type SermonSummary } from '$lib/library-public';
	import { buildResumeItems } from '$lib/resumeItems';
	import { getLang } from '$lib/lang.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import PageHeader from '$lib/components/PageHeader.svelte';
	import SectionHeader from '$lib/components/SectionHeader.svelte';
	import WorkCard from '$lib/components/WorkCard.svelte';
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
			listSermons(lang).catch(() => [] as SermonSummary[])
		]).then(([b, s]) => {
			books = b;
			sermons = s;
			loaded = true;
		});
		return () => window.removeEventListener('ochorus:sync', bump);
	});

	const items = $derived.by(() => {
		void ticks;
		return buildResumeItems(books, sermons);
	});
	// "In progress" excludes finished works; "Finished" is books whose last-opened
	// chapter is their last — the very split the two dashboard tiles count, so a
	// reader arriving from either tile lands on the matching section. The Finished
	// cards render with `complete`, which swaps the meter for a completion line.
	const inProgress = $derived(items.filter((i) => !i.finished));
	const finished = $derived(items.filter((i) => i.finished));
	const isEmpty = $derived(loaded && items.length === 0);
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

	{#if inProgress.length}
		<section class="pt-2">
			<SectionHeader title={t('settings.statInProgress')} />
			<div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
				{#each inProgress as item (item.key)}
					<WorkCard {item} />
				{/each}
			</div>
		</section>
	{/if}

	{#if finished.length}
		<!-- The Finished tile deep-links to #finished; the offset clears the sticky
		     header so the heading isn't hidden under it on arrival. -->
		<section id="finished" class="scroll-mt-24 pt-10">
			<SectionHeader title={t('settings.statFinished')} />
			<div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
				{#each finished as item (item.key)}
					<WorkCard {item} complete />
				{/each}
			</div>
		</section>
	{/if}
</div>
