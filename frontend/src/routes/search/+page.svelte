<script lang="ts">
	import { search, type SearchHit, type ChapterHit } from '$lib/library';
	import { getLang } from '$lib/lang.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { markSnippet } from '$lib/highlight';
	import { localizeHref } from '$lib/paraglide/runtime';
	import { goto } from '$app/navigation';

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

	type ResultRow = Row & { type: SearchHit['type'] };
	const rows = $derived<ResultRow[]>(hits.map((h) => ({ ...toRow(h), type: h.type })));

	// Cluster the flat result list into type sections in a fixed reading order —
	// navigational entities first, passages last — keeping only sections present.
	const GROUP_ORDER: { type: SearchHit['type']; labelKey: string }[] = [
		{ type: 'book', labelKey: 'search.groupBooks' },
		{ type: 'author', labelKey: 'search.groupAuthors' },
		{ type: 'topic', labelKey: 'search.groupTopics' },
		{ type: 'plan', labelKey: 'search.groupPlans' },
		{ type: 'chapter', labelKey: 'search.groupPassages' },
		{ type: 'sermon', labelKey: 'search.groupSermons' }
	];
	const groups = $derived.by(() => {
		const by = new Map<string, ResultRow[]>();
		for (const r of rows) {
			const arr = by.get(r.type);
			if (arr) arr.push(r);
			else by.set(r.type, [r]);
		}
		return GROUP_ORDER.filter((g) => by.has(g.type)).map((g) => ({
			type: g.type,
			labelKey: g.labelKey,
			rows: by.get(g.type)!
		}));
	});

	// Within the Passages section, collapse a book's chapter matches under the
	// book so "where does this theme live across the work" reads as a map, not a
	// scatter of unrelated-looking lines. Books over the preview cap get a toggle.
	const PASSAGE_PREVIEW = 3;
	let expandedBooks = $state(new Set<string>());

	type PassageBook = {
		slug: string;
		title: string;
		author: string;
		chapters: { key: string; order: number; title: string; snippet: string }[];
	};
	const passageBooks = $derived.by<PassageBook[]>(() => {
		const by = new Map<string, PassageBook>();
		for (const h of hits) {
			if (h.type !== 'chapter') continue;
			const c = h as ChapterHit;
			let g = by.get(c.book_slug);
			if (!g) {
				g = { slug: c.book_slug, title: c.book_title, author: c.author_name, chapters: [] };
				by.set(c.book_slug, g);
			}
			g.chapters.push({
				key: `${c.book_slug}:${c.chapter_order}`,
				order: c.chapter_order,
				title: c.chapter_title || c.book_title,
				snippet: c.snippet
			});
		}
		return [...by.values()];
	});

	function toggleBook(slug: string) {
		const next = new Set(expandedBooks);
		if (next.has(slug)) next.delete(slug);
		else next.add(slug);
		expandedBooks = next;
	}

	// --- Keyboard navigation ---------------------------------------------------
	// Flatten the *visible* leaf results (entity/sermon rows + the shown passage
	// chapters, in display order) so ↑/↓ walk them and Enter opens the active one.
	let activeIndex = $state(-1);
	const nav = $derived.by(() => {
		const keys: string[] = [];
		const map = new Map<string, string>();
		for (const g of groups) {
			if (g.type === 'chapter') {
				for (const pb of passageBooks) {
					const shown = expandedBooks.has(pb.slug)
						? pb.chapters
						: pb.chapters.slice(0, PASSAGE_PREVIEW);
					for (const ch of shown) {
						keys.push(ch.key);
						map.set(ch.key, `/books/${pb.slug}/${ch.order}`);
					}
				}
			} else {
				for (const row of g.rows) {
					keys.push(row.key);
					map.set(row.key, row.href);
				}
			}
		}
		return { keys, map };
	});
	const activeKey = $derived(
		activeIndex >= 0 && activeIndex < nav.keys.length ? nav.keys[activeIndex] : ''
	);

	// Keep the highlighted result in view as it moves.
	$effect(() => {
		if (activeKey) document.getElementById(`res-${activeKey}`)?.scrollIntoView({ block: 'nearest' });
	});

	function onKeydown(e: KeyboardEvent) {
		const n = nav.keys.length;
		if (!n) return;
		if (e.key === 'ArrowDown') {
			e.preventDefault();
			activeIndex = (activeIndex + 1) % n;
		} else if (e.key === 'ArrowUp') {
			e.preventDefault();
			activeIndex = activeIndex <= 0 ? n - 1 : activeIndex - 1;
		} else if (e.key === 'Enter') {
			const key = activeIndex >= 0 ? nav.keys[activeIndex] : nav.keys[0];
			const href = nav.map.get(key);
			if (href) goto(localizeHref(href));
		} else if (e.key === 'Escape') {
			activeIndex = -1;
		}
	}

	function onInput() {
		activeIndex = -1;
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
		onkeydown={onKeydown}
		type="search"
		autocomplete="off"
		role="combobox"
		aria-expanded={hits.length > 0}
		aria-controls="search-results"
		placeholder={t('search.placeholder')}
		aria-label={t('search.title')}
		class="w-full rounded-card border border-border bg-surface px-4 py-3 text-body text-text"
	/>

	<div class="mt-6" id="search-results">
		{#if loading}
			<div class="space-y-6" aria-hidden="true">
				{#each Array(4) as _, i (i)}
					<div class="animate-pulse space-y-2">
						<div class="h-3 w-1/4 rounded bg-surface-2"></div>
						<div class="h-4 w-2/3 rounded bg-surface-2"></div>
						<div class="h-3 w-full rounded bg-surface-2"></div>
					</div>
				{/each}
			</div>
		{:else if q.trim().length < 2}
			<p class="text-small text-muted">{t('search.prompt')}</p>
		{:else if ran && hits.length === 0}
			<p class="text-small text-muted">{t('search.noResults')} “{ran}”.</p>
		{:else}
			<p class="mb-4 text-small text-muted" aria-live="polite">
				{hits.length}
				{hits.length === 1 ? t('search.resultsOne') : t('search.resultsMany')}
			</p>
			<div class="space-y-8">
				{#each groups as g (g.type)}
					<section>
						<h2
							class="mb-2 flex items-baseline gap-2 text-small font-semibold uppercase tracking-wide text-muted"
						>
							{t(g.labelKey)}
							<span class="text-[0.78rem] font-normal tabular-nums text-muted/70">{g.rows.length}</span>
						</h2>
						{#if g.type === 'chapter'}
							<!-- Passages: matches collapsed under their book. -->
							<div class="space-y-5">
								{#each passageBooks as pb (pb.slug)}
									{@const expanded = expandedBooks.has(pb.slug)}
									{@const shown = expanded ? pb.chapters : pb.chapters.slice(0, PASSAGE_PREVIEW)}
									<div>
										<a
											href={localizeHref(`/books/${pb.slug}`)}
											class="text-small font-semibold text-text hover:text-accent hover:no-underline"
										>
											{pb.title} <span class="font-normal text-muted">· {pb.author}</span>
										</a>
										<ul class="mt-1 divide-y divide-border border-l border-border pl-3">
											{#each shown as ch (ch.key)}
												<li class="py-2.5">
													<a
														href={localizeHref(`/books/${pb.slug}/${ch.order}`)}
														id="res-{ch.key}"
														class="-mx-2 block rounded px-2 hover:no-underline"
														class:bg-surface-2={ch.key === activeKey}
													>
														<div class="text-small font-medium text-text">{ch.title}</div>
														{#if ch.snippet}
															<p class="mt-0.5 text-small text-muted">
																<!-- eslint-disable-next-line svelte/no-at-html-tags -->
																{@html mark(ch.snippet)}
															</p>
														{/if}
													</a>
												</li>
											{/each}
										</ul>
										{#if pb.chapters.length > PASSAGE_PREVIEW}
											<button
												type="button"
												onclick={() => toggleBook(pb.slug)}
												class="mt-1.5 pl-3 text-small font-semibold text-accent"
											>
												{#if expanded}
													{t('search.showLess')}
												{:else}
													+{pb.chapters.length - PASSAGE_PREVIEW} {t('search.morePassages')}
												{/if}
											</button>
										{/if}
									</div>
								{/each}
							</div>
						{:else}
							<ul class="divide-y divide-border">
								{#each g.rows as row (row.key)}
									<li class="py-4">
										<a
											href={localizeHref(row.href)}
											id="res-{row.key}"
											class="-mx-2 block rounded px-2 hover:no-underline"
											class:bg-surface-2={row.key === activeKey}
										>
											{#if row.meta}
												<div class="text-small text-muted">{row.meta}</div>
											{/if}
											<div class="text-body font-semibold text-text">{row.title}</div>
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
					</section>
				{/each}
			</div>
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
