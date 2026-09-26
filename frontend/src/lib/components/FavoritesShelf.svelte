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
	import { favorites } from '$lib/favorites.svelte';
	import { allProgress } from '$lib/progress';
	import {
		LEDGER_KINDS,
		buildLedger,
		buildShelves,
		type LedgerKind,
		type LedgerRow
	} from '$lib/bookshelf';
	import { getLang } from '$lib/lang.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { portraitPosition, portraitSrcset } from '$lib/portraits';
	import { relativeTime } from '$lib/relativeTime';
	import { initials } from '$lib/strings';
	import { hydrateSrc } from '$lib/hydrateSrc';
	import SectionHeader from '$lib/components/SectionHeader.svelte';
	import BookCover from '$lib/components/BookCover.svelte';
	import ProgressBar from '$lib/components/ProgressBar.svelte';
	import Icon from '$lib/components/Icon.svelte';

	/**
	 * "Bookshelf" on the signed-in home — a ledger of what the reader keeps:
	 * one numbered list, most recent first, of their books (from the same
	 * shelves /favorites builds, so a book they started without hearting is
	 * here too) and the authors, plans and sermons they've hearted. Each row
	 * says where the reader stands — progress, finished, to read — and when
	 * they last touched it, and filter pills narrow it to one kind.
	 *
	 * Client-side only (the homepage is prerendered and this is personal);
	 * renders nothing while empty. Titles resolve from the public list
	 * endpoints; a favorite whose work isn't in the current language keeps its
	 * slug-derived label rather than vanishing.
	 */
	const t = i18n.t;

	/** Rows shown before "Show all" takes over (the full list is /favorites). */
	const LIMIT = 8;

	const FILTER_LABEL: Record<LedgerKind, string> = {
		book: 'fav.groupBooks',
		author: 'fav.groupAuthors',
		plan: 'fav.groupPlans',
		sermon: 'fav.groupSermons'
	};
	const ICON = { book: 'book', author: 'book', plan: 'calendar', sermon: 'mic' } as const;

	let books = $state<BookSummary[]>([]);
	let authors = $state<Record<string, AuthorBio>>({});
	let plans = $state<Record<string, PlanSummary>>({});
	let sermons = $state<Record<string, SermonSummary>>({});
	let loaded = $state(false);
	let filter = $state<LedgerKind | 'all'>('all');

	// Reading progress is localStorage, not a rune: re-read it when an account
	// sync announces a change.
	let progressTicks = $state(0);

	onMount(() => {
		const bump = () => progressTicks++;
		window.addEventListener('ochorus:sync', bump);
		void load();
		return () => window.removeEventListener('ochorus:sync', bump);
	});

	async function load() {
		const lang = getLang();
		// Fetch all four catalogs concurrently; each is small and cached by the
		// browser. A failed catalog just means slug-derived labels for its kind.
		const [a, b, p, s] = await Promise.all([
			listAuthors(lang).catch(() => [] as AuthorBio[]),
			listBooks(lang).catch(() => [] as BookSummary[]),
			listPlans(lang).catch(() => [] as PlanSummary[]),
			listSermons(lang).catch(() => [] as SermonSummary[])
		]);
		const bySlug = <T extends { slug: string }>(xs: T[]) =>
			Object.fromEntries(xs.map((x) => [x.slug, x]));
		authors = bySlug(a);
		books = b;
		plans = bySlug(p);
		sermons = bySlug(s);
		loaded = true;
	}

	const rows = $derived.by(() => {
		void progressTicks;
		const favs = favorites.all();
		return buildLedger(buildShelves(books, favs, allProgress()), favs, (kind, slug) => {
			if (kind === 'author') return authors[slug] && { title: authors[slug].name };
			if (kind === 'plan') return plans[slug] && { title: plans[slug].title };
			return sermons[slug] && { title: sermons[slug].title, by: sermons[slug].author.name };
		});
	});

	// "All" plus a pill per kind the reader actually has — none for one kind.
	const pills = $derived.by(() => {
		const counts = new Map<LedgerKind, number>();
		for (const r of rows) counts.set(r.kind, (counts.get(r.kind) ?? 0) + 1);
		const kinds = LEDGER_KINDS.filter((k) => counts.has(k));
		if (kinds.length < 2) return [];
		return [
			{ value: 'all' as const, label: t('search.filterAll'), count: rows.length },
			...kinds.map((k) => ({ value: k, label: t(FILTER_LABEL[k]), count: counts.get(k)! }))
		];
	});
	const shown = $derived(
		(filter === 'all' ? rows : rows.filter((r) => r.kind === filter)).slice(0, LIMIT)
	);

	const when = (ts: number) => relativeTime(ts, getLang(), t('settings.syncJustNow'));

	/** The status column: where the reader stands with a book. */
	function status(r: LedgerRow): string {
		const s = r.shelf;
		if (!s) return '';
		if (s.status === 'finished') return t('fav.shelfFinished');
		if (s.status === 'toRead') return t('fav.shelfToRead');
		return `${s.pct}%`;
	}

	/** The last column: when the reader last touched it. */
	function activity(r: LedgerRow): string {
		if (!r.at) return '';
		const s = r.shelf;
		if (s?.status === 'reading') return t('fav.lastRead').replace('%d%', when(r.at));
		if (s?.status === 'finished') return when(r.at);
		return `${t('fav.saved')} · ${when(r.at)}`;
	}
</script>

{#if loaded && rows.length}
	<section class="page-col px-5 pt-14">
		<SectionHeader
			title={t('fav.yourFavorites')}
			href={localizeHref('/favorites')}
			linkText={t('search.showAll')}
		/>

		{#if pills.length}
			<div class="chip-scroller mb-3 flex gap-2">
				{#each pills as p (p.value)}
					<button
						type="button"
						class="chip"
						class:active={filter === p.value}
						aria-pressed={filter === p.value}
						onclick={() => (filter = p.value)}
					>
						{p.label}
						<span class="count">{p.count}</span>
					</button>
				{/each}
			</div>
		{/if}

		<ol class="border-t-2 border-text">
			{#each shown as r, i (`${r.kind}:${r.slug}`)}
				<li class="border-b border-border">
					<a
						href={localizeHref(r.href)}
						class="ledger-row group grid items-center gap-x-4 px-1 py-3 text-text hover:no-underline sm:gap-x-5 sm:px-2"
					>
						<span class="font-display text-small text-border-strong tabular-nums" aria-hidden="true"
							>{String(i + 1).padStart(2, '0')}</span
						>

						<span class="flex min-w-0 items-center gap-3 sm:gap-4">
							{#if r.shelf}
								<!-- The row names the book; the cover's own type would say it twice. -->
								<span class="flex w-10 shrink-0 justify-center" aria-hidden="true"
									><span class="w-8"><BookCover book={r.shelf.book} rounded="rounded-sm" /></span></span
								>
							{:else if r.kind === 'author' && authors[r.slug]?.photo_url}
								{@const url = authors[r.slug].photo_url}
								{@const source = { src: url, srcset: portraitSrcset(url) }}
								<img
									src={source.src}
									srcset={source.srcset}
									use:hydrateSrc={source}
									sizes="40px"
									width="40"
									height="40"
									alt=""
									loading="lazy"
									class="h-10 w-10 shrink-0 rounded-full border border-border object-cover"
									style="filter: grayscale(1); object-position: {portraitPosition(r.slug)}"
								/>
							{:else if r.kind === 'author'}
								<span
									class="font-display flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-accent-soft text-small font-semibold text-accent"
									aria-hidden="true">{initials(r.title)}</span
								>
							{:else}
								<span
									class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-surface-2 text-muted"
									aria-hidden="true"
								>
									<Icon name={ICON[r.kind]} size={16} />
								</span>
							{/if}
							<span class="min-w-0">
								<span
									class="block truncate font-display text-body font-semibold group-hover:text-accent"
									>{r.title}</span
								>
								{#if r.by}
									<span class="block truncate text-small text-muted">{r.by}</span>
								{/if}
							</span>
						</span>

						<span class="flex items-center justify-end gap-2.5 sm:justify-start">
							{#if r.shelf?.status === 'reading'}
								<span class="hidden w-28 sm:block">
									<ProgressBar percent={r.shelf.pct} label="{r.title}: {r.shelf.pct}%" />
								</span>
							{/if}
							<span
								class="text-small whitespace-nowrap"
								class:text-muted={r.shelf?.status !== 'finished'}
								class:font-semibold={r.shelf?.status === 'finished'}>{status(r)}</span
							>
						</span>

						<span class="hidden truncate text-small text-muted md:block">{activity(r)}</span>
					</a>
				</li>
			{/each}
		</ol>
	</section>
{/if}

<style>
	/* № · title · status · when — the last column joins at md, the status
	   widens to take its meter at sm. */
	.ledger-row {
		grid-template-columns: 1.5rem minmax(0, 1fr) auto;
	}
	@media (min-width: 640px) {
		.ledger-row {
			grid-template-columns: 2rem minmax(0, 1fr) 11rem;
		}
	}
	@media (min-width: 768px) {
		.ledger-row {
			grid-template-columns: 2rem minmax(0, 1fr) 11rem 10rem;
		}
	}
</style>
