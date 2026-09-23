<script lang="ts">
	import { onMount } from 'svelte';
	import { listSermons, type BookSummary, type SermonSummary } from '$lib/library-public';
	import { cachedResumeBooks, libraryBooks, unfinishedBookSlugs } from '$lib/resumeBooks';
	import { allProgress } from '$lib/progress';
	import { buildResumeItems } from '$lib/resumeItems';
	import { getLang } from '$lib/lang.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import WorkCard from '$lib/components/WorkCard.svelte';
	import SectionHeader from '$lib/components/SectionHeader.svelte';

	/**
	 * In-progress works (books and sermons) with a resume link. Progress comes
	 * from the local cache (which the sign-in merge keeps in step with the
	 * account); books and sermons join against their lists for titles and
	 * covers, each fetched lazily — only when unfinished progress of that kind
	 * exists, so most renders cost nothing extra. Books draw at mount from the
	 * cached summaries of the reader's in-progress books, then refresh from the
	 * network (`$lib/resumeBooks` says why: this strip sits above the hero, and
	 * one arriving late shoves the front page down). Works
	 * unknown in this language are skipped. A FINISHED work leaves this strip for
	 * the finished shelf (/reading#finished); the rest age off naturally as newer
	 * reads push them past the limit. Renders nothing when there's nothing in
	 * progress.
	 */
	let { limit = 4 }: { limit?: number } = $props();

	const t = i18n.t;

	// localStorage is read on mount (not during load) so a sign-in sync that
	// lands after navigation still shows up via the ochorus:sync event below.
	let ticks = $state(0);
	let bookList = $state<BookSummary[]>([]);
	let sermonList = $state<SermonSummary[] | null>(null);

	function fetchListsIfNeeded() {
		const progress = allProgress();
		if (unfinishedBookSlugs(progress).length) {
			const lang = getLang();
			if (!bookList.length) bookList = cachedResumeBooks(lang);
			libraryBooks(lang)
				.then((l) => (bookList = l))
				.catch(() => {});
		}
		if (sermonList === null && progress.some((p) => p.kind === 'sermon' && p.finished_at == null)) {
			listSermons(getLang())
				.then((l) => (sermonList = l))
				.catch(() => {});
		}
	}

	onMount(() => {
		const bump = () => {
			ticks++;
			fetchListsIfNeeded();
		};
		fetchListsIfNeeded();
		window.addEventListener('ochorus:sync', bump);
		return () => window.removeEventListener('ochorus:sync', bump);
	});

	// The resume-card list is built (and its deep-links composed) in one shared
	// place so the strip and the /reading page can't drift; the strip just takes
	// its own head. A finished work has left "Continue reading" for the finished
	// shelf, so the strip drops it before taking its head.
	const items = $derived.by(() => {
		void ticks;
		return buildResumeItems(bookList, sermonList ?? [])
			.filter((i) => !i.finished)
			.slice(0, limit);
	});
</script>

{#if items.length}
	<section class="page-col px-5 pt-14">
		<SectionHeader title={t('continue.title')} />
		<div class="grid gap-4 sm:grid-cols-2" class:lg:grid-cols-4={limit >= 4}>
			{#each items as item (item.key)}
				<WorkCard {item} />
			{/each}
		</div>
	</section>
{/if}
