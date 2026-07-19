<script lang="ts">
	import type { SermonSummary } from '$lib/library';
	import { SITE_URL } from '$lib/config';
	import { localizeHref, locales } from '$lib/paraglide/runtime';
	import { i18n } from '$lib/i18n.svelte';
	import { readingMinutes } from '$lib/reading';

	const t = i18n.t;

	let { data } = $props();
	const sermons = $derived<SermonSummary[]>(data.sermons);

	// --- Filters ----------------------------------------------------------------
	let queryText = $state('');
	let bibleBook = $state('');

	// Books of the Bible present on this shelf, in canonical order, with counts.
	const bookFacets = $derived.by(() => {
		const m = new Map<string, { name: string; order: number; count: number }>();
		for (const s of sermons) {
			if (!s.scripture_book) continue;
			const e = m.get(s.scripture_book);
			if (e) e.count++;
			else m.set(s.scripture_book, { name: s.scripture_book, order: s.scripture_book_order ?? 999, count: 1 });
		}
		return [...m.values()].sort((a, b) => a.order - b.order);
	});

	const filtered = $derived.by(() => {
		const q = queryText.trim().toLowerCase();
		return sermons.filter((s) => {
			if (bibleBook && s.scripture_book !== bibleBook) return false;
			if (!q) return true;
			return (
				s.title.toLowerCase().includes(q) ||
				s.author.name.toLowerCase().includes(q) ||
				s.scripture_ref.toLowerCase().includes(q)
			);
		});
	});

	const filtering = $derived(queryText.trim() !== '' || bibleBook !== '');

	// Group sermons by author, preserving the API's author-ordered sequence.
	const grouped = $derived.by(() => {
		const map = new Map<string, { name: string; slug: string; items: SermonSummary[] }>();
		for (const s of filtered) {
			const key = s.author.slug;
			if (!map.has(key)) map.set(key, { name: s.author.name, slug: key, items: [] });
			map.get(key)!.items.push(s);
		}
		return [...map.values()];
	});

</script>

<svelte:head>
	<title>{t('nav.sermons')} — Ochorus</title>
	<meta name="description" content={t('sermons.metaDescription')} />
	<link rel="canonical" href="{SITE_URL}{localizeHref('/sermons')}" />
	{#each locales as loc (loc)}
		<link
			rel="alternate"
			hreflang={loc}
			href="{SITE_URL}{localizeHref('/sermons', { locale: loc })}"
		/>
	{/each}
	<link rel="alternate" hreflang="x-default" href="{SITE_URL}/sermons" />
	<meta property="og:type" content="website" />
	<meta property="og:title" content="{t('nav.sermons')} — Ochorus" />
	<meta property="og:url" content="{SITE_URL}{localizeHref('/sermons')}" />
</svelte:head>

<div class="mx-auto max-w-3xl px-5 py-12">
	<header class="mb-10">
		<p class="mb-2 text-small font-semibold uppercase tracking-widest text-accent">{t('nav.sermons')}</p>
		<h1 class="text-display mb-3">{t('sermons.title')}</h1>
		<p class="text-body text-muted">
			{t('sermons.tagline')}
		</p>
	</header>

	<!-- Filter bar: free text + which book of the Bible the sermon expounds. -->
	<div class="mb-8 flex flex-wrap items-center gap-3">
		<input
			bind:value={queryText}
			type="search"
			autocomplete="off"
			placeholder={t('sermons.filterPlaceholder')}
			aria-label={t('sermons.filterPlaceholder')}
			class="min-w-0 flex-1 rounded-card border border-border bg-surface px-4 py-2.5 text-body text-text"
		/>
		<select
			bind:value={bibleBook}
			aria-label={t('sermons.allBooks')}
			class="rounded-card border border-border bg-surface px-3 py-2.5 text-small text-text"
		>
			<option value="">{t('sermons.allBooks')}</option>
			{#each bookFacets as b (b.name)}
				<option value={b.name}>{b.name} ({b.count})</option>
			{/each}
		</select>
		{#if filtering}
			<button
				class="btn btn-ghost !py-2"
				onclick={() => {
					queryText = '';
					bibleBook = '';
				}}>{t('sermons.clear')}</button
			>
		{/if}
	</div>

	{#if filtering}
		<p class="mb-6 text-small text-muted" aria-live="polite">
			{filtered.length}
			{filtered.length === 1 ? t('sermons.matchOne') : t('sermons.matches')}
		</p>
	{/if}

	{#if grouped.length}
		<div class="space-y-10">
			{#each grouped as group (group.slug)}
				<section>
					<h2 class="mb-3 text-h3">
						<a href={localizeHref(`/authors/${group.slug}`)} class="!text-text hover:underline">{group.name}</a>
					</h2>
					<ul class="divide-y divide-border">
						{#each group.items as sermon (sermon.slug)}
							<li>
								<a
									href={localizeHref(`/sermons/${sermon.slug}`)}
									class="flex items-baseline justify-between gap-3 py-3 hover:no-underline"
								>
									<span class="flex-1">
										<span class="block text-body font-medium text-text">{sermon.title}</span>
										{#if sermon.scripture_ref}
											<span class="text-small text-accent">{sermon.scripture_ref}</span>
										{/if}
									</span>
									<span class="shrink-0 text-[0.8rem] text-muted">{readingMinutes(sermon.word_count)} {t('common.min')}</span>
								</a>
							</li>
						{/each}
					</ul>
				</section>
			{/each}
		</div>
	{:else}
		<p class="text-body text-muted">
			{filtering ? t('sermons.noMatches') : t('sermons.empty')}
		</p>
	{/if}
</div>
