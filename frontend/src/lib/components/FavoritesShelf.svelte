<script lang="ts">
	import { onMount } from 'svelte';
	import { authorPath } from '$lib/originals';
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
	import { getLang } from '$lib/lang.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { unslug } from '$lib/strings';
	import SectionHeader from '$lib/components/SectionHeader.svelte';

	/**
	 * "Your favorites" — the authors, books, plans and sermons the reader has
	 * hearted, as links grouped by type. Client-side only (the homepage is
	 * prerendered and this is personal); renders nothing while empty. Titles
	 * resolve from the public list endpoints; a favorite whose work isn't in
	 * the current language simply shows its slug-derived label.
	 */
	const t = i18n.t;

	const HREF: Record<string, (slug: string) => string> = {
		author: (s) => authorPath(s),
		book: (s) => `/books/${s}`,
		plan: (s) => `/plans/${s}`,
		sermon: (s) => `/sermons/${s}`
	};
	const GROUP_LABEL: Record<string, string> = {
		author: 'fav.groupAuthors',
		book: 'fav.groupBooks',
		plan: 'fav.groupPlans',
		sermon: 'fav.groupSermons'
	};

	let titles = $state<Record<string, string>>({});
	let loaded = $state(false);

	onMount(async () => {
		const lang = getLang();
		// Fetch all four catalogs concurrently; each is small and cached by the
		// browser. A failed catalog just means slug-derived labels for its kind.
		const [authors, books, plans, sermons] = await Promise.all([
			listAuthors(lang).catch(() => [] as AuthorBio[]),
			listBooks(lang).catch(() => [] as BookSummary[]),
			listPlans(lang).catch(() => [] as PlanSummary[]),
			listSermons(lang).catch(() => [] as SermonSummary[])
		]);
		const map: Record<string, string> = {};
		for (const a of authors) map[`author:${a.slug}`] = a.name;
		for (const b of books) map[`book:${b.slug}`] = b.title;
		for (const p of plans) map[`plan:${p.slug}`] = p.title;
		for (const s of sermons) map[`sermon:${s.slug}`] = s.title;
		titles = map;
		loaded = true;
	});

	const titleOf = (e: FavoriteEntry) => titles[`${e.kind}:${e.slug}`] ?? unslug(e.slug);

	const groups = $derived.by(() => {
		const by = new Map<string, FavoriteEntry[]>();
		for (const e of favorites.all()) {
			const arr = by.get(e.kind) ?? [];
			arr.push(e);
			by.set(e.kind, arr);
		}
		return (['author', 'book', 'plan', 'sermon'] as const)
			.filter((k) => by.has(k))
			.map((k) => ({ kind: k, entries: by.get(k)! }));
	});
</script>

{#if loaded && groups.length}
	<section class="page-col px-5 pt-14">
		<SectionHeader
			title={t('fav.yourFavorites')}
			href={localizeHref('/favorites')}
			linkText={t('search.showAll')}
		/>
		<div class="space-y-4">
			{#each groups as g (g.kind)}
				<div class="flex flex-wrap items-baseline gap-2">
					<span class="w-24 shrink-0 section-label">
						{t(GROUP_LABEL[g.kind])}
					</span>
					{#each g.entries as e (e.slug)}
						<a
							href={localizeHref(HREF[e.kind](e.slug))}
							class="tag"
						>
							♥ {titleOf(e)}
						</a>
					{/each}
				</div>
			{/each}
		</div>
	</section>
{/if}
