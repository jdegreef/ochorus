<script lang="ts">
	/**
	 * "Insert from the library": one search across books, sermons, plans,
	 * articles, authors, topics and sourced quotes. Each result arrives with the
	 * block that inserts it; the panel just hands that block up. Results say
	 * whether they reach the language being edited — one that doesn't is left
	 * out of that language's email (there is no English fallback).
	 */
	import {
		searchLibraryForEmail,
		type EmailBlock,
		type LibrarySearchKind,
		type LibrarySearchResult
	} from '$lib/library-admin';

	let {
		locale,
		localeName = locale,
		onInsert,
		onClose
	}: {
		locale: string;
		localeName?: string;
		/** Returns whether the block was added. */
		onInsert: (block: EmailBlock) => boolean;
		onClose: () => void;
	} = $props();

	const KIND_LABELS: Record<LibrarySearchKind, string> = {
		author: 'Authors',
		book: 'Books',
		sermon: 'Sermons',
		plan: 'Plans',
		article: 'Articles',
		topic: 'Topics',
		quote: 'Quotes'
	};

	let query = $state('');
	let kind = $state<LibrarySearchKind | 'all'>('all');
	let results = $state<LibrarySearchResult[]>([]);
	let counts = $state<Partial<Record<LibrarySearchKind, number>>>({});
	let searching = $state(false);
	let failed = $state(false);
	let inserted = $state<string | null>(null);

	const shown = $derived(kind === 'all' ? results : results.filter((r) => r.kind === kind));
	const kinds = $derived(
		(Object.keys(KIND_LABELS) as LibrarySearchKind[]).filter((k) => (counts[k] ?? 0) > 0)
	);

	$effect(() => {
		const q = query.trim();
		failed = false;
		searching = false;
		if (q.length < 2) {
			results = [];
			counts = {};
			return;
		}
		const controller = new AbortController();
		const timer = setTimeout(async () => {
			searching = true;
			failed = false;
			try {
				const data = await searchLibraryForEmail(q, controller.signal);
				results = data.results;
				counts = data.counts;
				if (kind !== 'all' && !data.counts[kind]) kind = 'all';
			} catch {
				if (!controller.signal.aborted) failed = true;
			} finally {
				if (!controller.signal.aborted) searching = false;
			}
		}, 250);
		// A newer query supersedes this one: never let a slow, older search land last.
		return () => {
			clearTimeout(timer);
			controller.abort();
		};
	});

	function insert(r: LibrarySearchResult) {
		if (!onInsert($state.snapshot(r.block) as EmailBlock)) return;
		inserted = r.key;
		setTimeout(() => {
			if (inserted === r.key) inserted = null;
		}, 1500);
	}
</script>

<aside class="flex h-full flex-col gap-3" aria-label="Insert from the library">
	<div class="flex items-center justify-between gap-2">
		<h2 class="text-h3">Insert from the library</h2>
		<button class="btn btn-ghost btn-sm" onclick={onClose} aria-label="Close the library panel">✕</button>
	</div>
	<!-- svelte-ignore a11y_autofocus -->
	<input
		class="w-full rounded-md border border-border bg-surface p-2 text-body"
		type="search"
		aria-label="Search the library"
		placeholder="A title, an author, words from a quote…"
		bind:value={query}
		autofocus
	/>
	{#if kinds.length}
		<div class="flex flex-wrap gap-1" role="group" aria-label="Show only">
			<button class="rounded-full border px-2.5 py-0.5 text-micro {kind === 'all' ? 'border-accent bg-accent text-accent-contrast' : 'border-border text-text'}" aria-pressed={kind === 'all'} onclick={() => (kind = 'all')}>All</button>
			{#each kinds as k (k)}
				<button class="rounded-full border px-2.5 py-0.5 text-micro {kind === k ? 'border-accent bg-accent text-accent-contrast' : 'border-border text-text'}" aria-pressed={kind === k} onclick={() => (kind = k)}>{KIND_LABELS[k]} {counts[k]}</button>
			{/each}
		</div>
	{/if}

	<div class="min-h-0 flex-1 overflow-y-auto" aria-live="polite">
		{#if query.trim().length < 2}
			<p class="text-small text-muted">Type at least two letters. Results drop into the email being edited ({localeName}), at the end.</p>
		{:else if searching && !results.length}
			<p class="text-small text-muted">Searching…</p>
		{:else if failed}
			<p class="text-small text-danger">The search didn't go through — try again.</p>
		{:else if !shown.length}
			<p class="text-small text-muted">Nothing found.</p>
		{:else}
			<ul class="space-y-2">
				{#each shown as r (r.key)}
					<li class="flex items-start gap-3 rounded-md border border-border bg-surface p-2">
						{#if r.image}
							<img src={r.image} alt="" class="w-10 shrink-0 object-cover {r.kind === 'author' ? 'h-10 rounded-full' : 'h-14 rounded-sm'}" />
						{/if}
						<div class="min-w-0 flex-1">
							<p class="text-micro font-semibold uppercase tracking-wide text-muted">{KIND_LABELS[r.kind].replace(/s$/, '')}</p>
							<p class="text-small text-text {r.kind === 'quote' ? 'italic' : 'font-semibold'} line-clamp-3">{r.title}</p>
							{#if r.subtitle}<p class="text-micro text-muted">{r.subtitle}</p>{/if}
							{#if r.kind === 'quote'}
								<!-- A quote is inserted as its words, so it shows in any language as written. -->
								{#if r.languages.length && !r.languages.includes(locale)}
									<p class="text-micro text-warning">Written in {r.languages[0]} — it shows in this {localeName} email as is</p>
								{/if}
							{:else if r.languages.length}
								<p class="text-micro {r.languages.includes(locale) ? 'text-muted' : 'text-warning'}">
									{r.languages.includes(locale) ? r.languages.join(' · ') : `Not in ${localeName} — left out of this email`}
								</p>
							{/if}
						</div>
						<button class="btn btn-ghost btn-sm shrink-0" onclick={() => insert(r)}>{inserted === r.key ? 'Added ✓' : 'Insert'}</button>
					</li>
				{/each}
			</ul>
			{#if kind !== 'all' && (counts[kind] ?? 0) > shown.length}
				<p class="mt-2 text-micro text-muted">Showing {shown.length} of {counts[kind]} — add words to narrow the search.</p>
			{:else if kind === 'all' && kinds.some((k) => (counts[k] ?? 0) > results.filter((r) => r.kind === k).length)}
				<p class="mt-2 text-micro text-muted">The first few of each kind — add words to narrow the search.</p>
			{/if}
		{/if}
	</div>
</aside>
