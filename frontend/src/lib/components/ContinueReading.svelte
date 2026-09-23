<script lang="ts">
	import { onMount } from 'svelte';
	import { listSermons, type CoverBook, type SermonSummary } from '$lib/library-public';
	import {
		cachedResumeBooks,
		knownAbsentBooks,
		libraryBooks,
		unfinishedBookSlugs
	} from '$lib/resumeBooks';
	import { workSlugKey } from '$lib/reading-schema';
	import type { ResumeItem } from '$lib/resumeItems';
	import { allProgress } from '$lib/progress';
	import { buildResumeItems } from '$lib/resumeItems';
	import { getLang } from '$lib/lang.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import WorkCard, { placeholder } from '$lib/components/WorkCard.svelte';
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
	 * drawable yet — a cache miss, a changed cover set, a sermon — holds its
	 * card's space AND its place with a placeholder until its list lands: the
	 * strip is drawn as slots in recency order, so a card never moves under the
	 * reader's thumb when a newer work fills in ahead of it. A book the
	 * language's last list did not have gets no slot at all. Works
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
	const drawable = $derived.by(() => {
		void ticks;
		return buildResumeItems(bookList, sermonList ?? []).filter((i) => !i.finished);
	});

	type Slot = { key: string; item: ResumeItem } | { key: string; pending: 'book' | 'sermon' };

	// The strip's cards. Settled, they are simply the first `limit` drawable
	// works. While a list is still coming, they are the first `limit` unfinished
	// works IN RECENCY ORDER, each either drawn or held by a placeholder in its
	// own place — the strip is its final height, and its final order, from mount.
	const slots = $derived.by<Slot[]>(() => {
		void ticks;
		if (!loadingBooks && !loadingSermons) {
			return drawable.slice(0, limit).map((item) => ({ key: item.key, item }));
		}
		const byKey = new Map(drawable.map((i) => [i.key, i]));
		const absent = knownAbsentBooks(getLang());
		return allProgress()
			.filter(
				(p) =>
					p.finished_at == null &&
					(p.kind === 'sermon' || (p.kind === 'book' && !absent.has(p.slug)))
			)
			.slice(0, limit)
			.map((p) => {
				const key = workSlugKey(p.kind, p.slug);
				const item = byKey.get(key);
				return item ? { key, item } : { key, pending: p.kind as 'book' | 'sermon' };
			});
	});
	const busy = $derived(slots.some((s) => 'pending' in s));
</script>

{#if slots.length}
	<!-- `aria-busy` while any card is still a placeholder: the heading is real,
	     the cards under it are coming, and a screen reader should say so rather
	     than announce a heading with nothing beneath it. -->
	<section class="page-col px-5 pt-14" aria-busy={busy}>
		<SectionHeader title={t('continue.title')} />
		<div class="grid gap-4 sm:grid-cols-2" class:lg:grid-cols-4={limit >= 4}>
			{#each slots as slot (slot.key)}
				{#if 'item' in slot}
					<WorkCard item={slot.item} />
				{:else}
					{@render placeholder(slot.pending)}
				{/if}
			{/each}
		</div>
	</section>
{/if}
