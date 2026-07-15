<script lang="ts">
	import { search, type SearchHit } from '$lib/library';
	import { getLang } from '$lib/lang.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { markSnippet } from '$lib/highlight';
	import { localizeHref } from '$lib/paraglide/runtime';

	const t = i18n.t;

	// One flat shape for every hit type, so the list renders uniformly (and so
	// grouping by type is a small step from here). `label` is the type chip;
	// `meta` is the muted line under the title; `snippet` may be empty for
	// entities with no prose.
	type Row = {
		key: string;
		label: string;
		href: string;
		title: string;
		meta: string;
		snippet: string;
	};

	function toRow(hit: SearchHit): Row {
		switch (hit.type) {
			case 'author':
				return {
					key: 'author:' + hit.author_slug,
					label: t('search.typeAuthor'),
					href: `/authors/${hit.author_slug}`,
					title: hit.author_name,
					meta: '',
					snippet: hit.snippet
				};
			case 'book':
				return {
					key: 'book:' + hit.book_slug,
					label: t('search.typeBook'),
					href: `/books/${hit.book_slug}`,
					title: hit.book_title,
					meta: hit.author_name,
					snippet: hit.snippet
				};
			case 'topic':
				return {
					key: 'topic:' + hit.topic_slug,
					label: t('search.typeTopic'),
					href: `/topics/${hit.topic_slug}`,
					title: hit.topic_title,
					meta: '',
					snippet: hit.snippet
				};
			case 'plan':
				return {
					key: 'plan:' + hit.plan_slug,
					label: t('search.typePlan'),
					href: `/plans/${hit.plan_slug}`,
					title: hit.plan_title,
					meta: '',
					snippet: hit.snippet
				};
			case 'sermon':
				return {
					key: 'sermon:' + hit.sermon_slug,
					label: t('search.typeSermon'),
					href: `/sermons/${hit.sermon_slug}`,
					title: hit.sermon_title,
					meta: hit.scripture_ref
						? `${hit.author_name} · ${hit.scripture_ref}`
						: hit.author_name,
					snippet: hit.snippet
				};
			default:
				return {
					key: `chapter:${hit.book_slug}:${hit.chapter_order}`,
					label: t('search.typeChapter'),
					href: `/books/${hit.book_slug}/${hit.chapter_order}`,
					title: hit.chapter_title || hit.book_title,
					meta: `${hit.book_title} · ${hit.author_name}`,
					snippet: hit.snippet
				};
		}
	}
	let q = $state('');
	let hits = $state<SearchHit[]>([]);
	let loading = $state(false);
	let ran = $state('');
	let timer: ReturnType<typeof setTimeout> | undefined;

	const rows = $derived(hits.map(toRow));

	function onInput() {
		clearTimeout(timer);
		const term = q.trim();
		if (term.length < 2) {
			hits = [];
			ran = '';
			return;
		}
		timer = setTimeout(async () => {
			loading = true;
			try {
				const res = await search(term, getLang());
				hits = res.results;
				ran = res.query;
			} finally {
				loading = false;
			}
		}, 250);
	}

	// Server snippets arrive with matches wrapped in full-text markers; markSnippet
	// escapes them and swaps the markers for <mark> (shared with the in-book search).
	const mark = markSnippet;
</script>

<svelte:head><title>{t('search.title')} — Ochorus</title></svelte:head>

<div class="mx-auto max-w-2xl px-5 py-10">
	<h1 class="text-h1 mb-5">{t('search.title')}</h1>

	<input
		bind:value={q}
		oninput={onInput}
		type="search"
		autocomplete="off"
		placeholder={t('search.placeholder')}
		aria-label={t('search.title')}
		class="w-full rounded-card border border-border bg-surface px-4 py-3 text-body text-text"
	/>

	<div class="mt-6">
		{#if loading}
			<p class="text-small text-muted">…</p>
		{:else if q.trim().length < 2}
			<p class="text-small text-muted">{t('search.prompt')}</p>
		{:else if ran && hits.length === 0}
			<p class="text-small text-muted">{t('search.noResults')} “{ran}”.</p>
		{:else}
			<ul class="divide-y divide-border">
				{#each rows as row (row.key)}
					<li class="py-4">
						<a href={localizeHref(row.href)} class="block hover:no-underline">
							<div class="flex items-center gap-2 text-small text-muted">
								<span
									class="rounded-full bg-surface-2 px-2 py-0.5 text-[0.68rem] font-semibold uppercase tracking-wide text-accent"
								>
									{row.label}
								</span>
								{#if row.meta}<span>{row.meta}</span>{/if}
							</div>
							<div class="mt-1 text-body font-semibold text-text">{row.title}</div>
							{#if row.snippet}
								<p class="mt-1 text-small text-muted">
									<!-- eslint-disable-next-line svelte/no-at-html-tags -->
									{@html mark(row.snippet)}
								</p>
							{/if}
						</a>
					</li>
				{/each}
			</ul>
		{/if}
	</div>
</div>

<style>
	:global(.text-muted mark) {
		background: color-mix(in srgb, var(--gold) 30%, transparent);
		color: var(--text);
		border-radius: 3px;
		padding: 0 0.15em;
	}
</style>
