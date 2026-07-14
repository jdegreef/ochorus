<script lang="ts">
	import { search, type SearchHit } from '$lib/library';
	import { getLang } from '$lib/lang.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { markSnippet } from '$lib/highlight';
	import { localizeHref } from '$lib/paraglide/runtime';

	const t = i18n.t;
	let q = $state('');
	let hits = $state<SearchHit[]>([]);
	let loading = $state(false);
	let ran = $state('');
	let timer: ReturnType<typeof setTimeout> | undefined;

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
				{#each hits as hit (hit.type === 'sermon' ? 'sermon:' + hit.sermon_slug : hit.book_slug + ':' + hit.chapter_order)}
					<li class="py-4">
						{#if hit.type === 'sermon'}
							<a href={localizeHref(`/sermons/${hit.sermon_slug}`)} class="block hover:no-underline">
								<div class="text-small text-muted">
									Sermon · {hit.author_name}{#if hit.scripture_ref}
										· {hit.scripture_ref}{/if}
								</div>
								<div class="text-body font-semibold text-text">{hit.sermon_title}</div>
								<p class="mt-1 text-small text-muted">
									<!-- eslint-disable-next-line svelte/no-at-html-tags -->
									{@html mark(hit.snippet)}
								</p>
							</a>
						{:else}
							<a
								href={localizeHref(`/books/${hit.book_slug}/${hit.chapter_order}`)}
								class="block hover:no-underline"
							>
								<div class="text-small text-muted">
									{hit.book_title} · {hit.author_name}
								</div>
								<div class="text-body font-semibold text-text">{hit.chapter_title}</div>
								<p class="mt-1 text-small text-muted">
									<!-- eslint-disable-next-line svelte/no-at-html-tags -->
									{@html mark(hit.snippet)}
								</p>
							</a>
						{/if}
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
