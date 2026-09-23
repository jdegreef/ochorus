<script lang="ts">
	import { onMount } from 'svelte';
	import { listSermons, type CoverBook, type SermonSummary } from '$lib/library-public';
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
	 * exists, so most renders cost nothing extra.
	 *
	 * This strip sits ABOVE the hero, so it must not arrive late and shove the
	 * front page down. Books draw at mount from this build's cache of the
	 * reader's in-progress books (`$lib/resumeBooks`); any in-progress work not
	 * drawable yet — a cache miss, a new deploy, a sermon — holds its card's
	 * space with a placeholder of the same height until its list lands. Works
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
	let bookList = $state<CoverBook[]>([]);
	let sermonList = $state<SermonSummary[] | null>(null);
	// Lists still in flight — while one is, its works get placeholders.
	let loadingBooks = $state(false);
	let loadingSermons = $state(false);

	function fetchListsIfNeeded() {
		const progress = allProgress();
		if (unfinishedBookSlugs(progress).length) {
			const lang = getLang();
			if (!bookList.length) bookList = cachedResumeBooks(lang);
			loadingBooks = true;
			libraryBooks(lang)
				.then((l) => (bookList = l))
				.catch(() => {})
				.finally(() => (loadingBooks = false));
		}
		if (sermonList === null && progress.some((p) => p.kind === 'sermon' && p.finished_at == null)) {
			loadingSermons = true;
			listSermons(getLang())
				.then((l) => (sermonList = l))
				.catch(() => {})
				.finally(() => (loadingSermons = false));
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

	// How many cards the strip WILL hold, while a list is still coming: one per
	// unfinished work, up to the limit. The cards not drawable yet are reserved
	// as placeholders, so the strip is its final height from mount.
	const placeholders = $derived.by(() => {
		void ticks;
		if (!loadingBooks && !loadingSermons) return 0;
		const unfinished = allProgress().filter(
			(p) => (p.kind === 'book' || p.kind === 'sermon') && p.finished_at == null
		).length;
		return Math.max(0, Math.min(unfinished, limit) - items.length);
	});
</script>

{#if items.length || placeholders}
	<section class="page-col px-5 pt-14">
		<SectionHeader title={t('continue.title')} />
		<div class="grid gap-4 sm:grid-cols-2" class:lg:grid-cols-4={limit >= 4}>
			{#each items as item (item.key)}
				<WorkCard {item} />
			{/each}
			{#each { length: placeholders }, i (i)}
				<!-- WorkCard's frame and cover box, so it is exactly a card's height:
				     a border, p-4, and a w-14 3:4 cover set the row. -->
				<div
					class="flex gap-4 rounded-card border border-border p-4"
					data-testid="work-card-placeholder"
					aria-hidden="true"
				>
					<div class="aspect-[3/4] w-14 shrink-0 animate-pulse rounded-sm bg-surface-2"></div>
					<div class="min-w-0 flex-1 self-center">
						<div class="h-3 w-3/4 animate-pulse rounded bg-surface-2"></div>
						<div class="mt-2 h-3 w-1/2 animate-pulse rounded bg-surface-2"></div>
					</div>
				</div>
			{/each}
		</div>
	</section>
{/if}
