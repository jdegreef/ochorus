<script lang="ts">
	import { onMount } from 'svelte';
	import { listSermons, type BookSummary, type SermonSummary } from '$lib/library-public';
	import BookCover from '$lib/components/BookCover.svelte';
	import { allProgress } from '$lib/progress';
	import { workSlugKey } from '$lib/reading-schema';
	import { bookProgressPercent } from '$lib/reading';
	import { getLang } from '$lib/lang.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import Icon from '$lib/components/Icon.svelte';
	import ProgressBar from '$lib/components/ProgressBar.svelte';
	import SectionHeader from '$lib/components/SectionHeader.svelte';

	/**
	 * In-progress works (books and sermons) with a resume link. Progress comes
	 * from the local cache (which the sign-in merge keeps in step with the
	 * account); books join against the provided list for titles and covers,
	 * sermons against a lazily fetched sermon list — fetched only when sermon
	 * progress actually exists, so most renders cost nothing extra. Works
	 * unknown in this language are skipped; a book stays here through its last
	 * chapter (opening the last chapter isn't finishing it) and ages off
	 * naturally as newer reads push it past the limit. Renders nothing when
	 * there's nothing in progress.
	 */
	let { books, limit = 4 }: { books: BookSummary[]; limit?: number } = $props();

	const t = i18n.t;

	// localStorage is read on mount (not during load) so a sign-in sync that
	// lands after navigation still shows up via the ochorus:sync event below.
	let ticks = $state(0);
	let sermonList = $state<SermonSummary[] | null>(null);

	function fetchSermonsIfNeeded() {
		if (sermonList === null && allProgress().some((p) => p.kind === 'sermon')) {
			listSermons(getLang())
				.then((l) => (sermonList = l))
				.catch(() => {});
		}
	}

	onMount(() => {
		const bump = () => {
			ticks++;
			fetchSermonsIfNeeded();
		};
		fetchSermonsIfNeeded();
		window.addEventListener('ochorus:sync', bump);
		return () => window.removeEventListener('ochorus:sync', bump);
	});

	type Item = {
		kind: 'book' | 'sermon';
		key: string;
		href: string;
		title: string;
		author: string;
		/** The full book, for books — passed to <BookCover> so plate (SVG) covers
		 * get their title drawn, exactly as on the shelves. Absent for sermons. */
		book?: BookSummary;
		/** null for sermons — a single document has no chapter meter. */
		pct: number | null;
		meta: string;
	};

	const items = $derived.by(() => {
		void ticks;
		const bySlug = new Map(books.map((b) => [b.slug, b]));
		const sermonBySlug = new Map((sermonList ?? []).map((s) => [s.slug, s]));
		return allProgress()
			.map((p): Item | null => {
				if (p.kind === 'sermon') {
					const sermon = sermonBySlug.get(p.slug);
					if (!sermon) return null;
					const resume = p.paragraph_index > 0 ? `?p=${p.paragraph_index}` : '';
					return {
						key: workSlugKey(p.kind, p.slug),
						kind: 'sermon',
						href: `/sermons/${p.slug}${resume}`,
						title: sermon.title,
						author: sermon.author.name,
						pct: null,
						// Scripture ref gives the (meter-less) sermon card some substance.
						meta: sermon.scripture_ref
							? `${t('search.typeSermon')} · ${sermon.scripture_ref}`
							: t('search.typeSermon')
					};
				}
				const book = bySlug.get(p.slug);
				if (!book) return null;
				// order is the chapter currently open. Treat it as in-progress, not
				// finished — the midpoint estimate keeps the book visible (and honest
				// about position) all the way through the last chapter.
				const pct = bookProgressPercent(p.order, book.chapter_count);
				return {
					kind: 'book',
					key: workSlugKey(p.kind, p.slug),
					href: `/books/${book.slug}/${p.order}`,
					title: book.title,
					author: book.author.name,
					book,
					pct,
					meta: `${t('continue.chapter')} ${p.order} / ${book.chapter_count} · ${pct}%`
				};
			})
			.filter((x) => x !== null)
			.slice(0, limit);
	});
</script>

{#if items.length}
	<section class="page-col px-5 pt-14">
		<SectionHeader title={t('continue.title')} />
		<div class="grid gap-4 sm:grid-cols-2" class:lg:grid-cols-4={limit >= 4}>
			{#each items as item (item.key)}
				<a
					href={localizeHref(item.href)}
					class="group flex gap-4 rounded-card border border-border p-4 hover:bg-surface-2 hover:no-underline"
				>
					{#if item.book}
						<!-- Draw through BookCover, not a bare <img>: a plate (SVG) ground
						     carries no title in the file, so a raw image shows a blank
						     coloured tile — BookCover sets the title over it, as the
						     shelves do. -->
						<div class="w-14 shrink-0">
							<BookCover book={item.book} rounded="rounded-sm" />
						</div>
					{:else}
						<!-- Sermons have no cover; a soft mic tile (matching SermonCard's
						     visual language) reads as intentional, not a blank block. -->
						<div class="sermon-thumb flex aspect-[3/4] w-14 shrink-0 items-center justify-center rounded-sm border shadow-sm">
							<Icon name="mic" size={22} />
						</div>
					{/if}
					<div class="min-w-0 flex-1 self-center">
						<div class="truncate text-small font-semibold text-text">{item.title}</div>
						<div class="mt-0.5 truncate text-small text-muted">{item.author}</div>
						{#if item.pct !== null}
							<div class="mt-2">
								<ProgressBar percent={item.pct} label="{item.title}: {item.meta}" />
							</div>
						{/if}
						<div class="mt-1 text-micro text-muted">{item.meta}</div>
					</div>
				</a>
			{/each}
		</div>
	</section>
{/if}

<style>
	/* Sermon thumbnail: a soft, accent-tinted tile with the mic glyph, sized to
	   the same footprint as book covers. Theme-aware via the shared tokens. */
	.sermon-thumb {
		color: var(--color-accent);
		border-color: var(--color-accent-soft-border);
		background: linear-gradient(155deg, var(--color-accent-soft), var(--color-surface-2));
	}
</style>
