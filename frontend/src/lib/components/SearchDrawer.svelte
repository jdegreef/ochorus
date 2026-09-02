<script lang="ts">
	import DrawerShell from '$lib/components/DrawerShell.svelte';
	import { getBook, getChapter } from '$lib/library-public';
	import { getLang } from '$lib/lang.svelte';
	import { createLimiter } from '$lib/limiter';
	import { i18n } from '$lib/i18n.svelte';
	import { escapeHtml, windowAt } from '$lib/highlight';
	import { normalizeForSearch, firstMatchSpan } from '$lib/searchNormalize';
	import { chapterLabel } from '$lib/reading';
	import { localizeHref } from '$lib/href';
	import { scopedSearchHref } from '$lib/searchState';

	/**
	 * In-book search: a slide-over that indexes every chapter of the current book
	 * (fetched once, then served from the service-worker cache — so it works
	 * offline once the book has been opened) and searches the plain text of each
	 * paragraph. Because the index is paragraph-granular, a result links straight
	 * to the matching paragraph via ?p=, the same anchor bookmarks and highlights
	 * use.
	 *
	 * Matching is normalized: text and query are folded (case + diacritics +
	 * curly quotes), and for ENGLISH books each word is Porter-stemmed, so
	 * "promise" finds "promises" and "prayers" finds "prayer". Different roots
	 * ("praying" ↔ "prayer") still don't fold — so every state offers the way up
	 * to the server's search of the same book (`/search?in=book:…`), which stems
	 * cross-root and ranks; from there one click widens to the whole library.
	 * Device → book → library, and the reader can always see which rung they're on.
	 */
	let {
		slug,
		open = $bindable(false)
	}: {
		slug: string;
		open?: boolean;
	} = $props();

	const t = i18n.t;

	// `norm` is the fold-/stem-normalized text the query matches against; `text`
	// stays raw for the snippet, so the highlight marks the real word.
	type Para = { order: number; title: string; p: number; text: string; norm: string };
	type Hit = { order: number; title: string; p: number; snippet: string };

	let input = $state<HTMLInputElement>();

	// The flattened paragraph index for the loaded book, and which book it's for.
	let indexed = $state<Para[]>([]);
	let indexedSlug = '';
	let indexing = $state(false);
	// Stem only English content (Porter's rules would mangle other scripts).
	let indexEnglish = $state(false);

	let query = $state('');
	const MAX_RESULTS = 80;

	/** Snippet for a hit: a window around the literal match, or — when the match
	 *  was found only after normalization — around the actual inflected word. */
	function snippetFor(text: string, q: string): string {
		const lit = text.toLowerCase().indexOf(q.toLowerCase());
		if (lit >= 0) return windowAt(text, lit, q.length);
		const span = firstMatchSpan(text, q, indexEnglish);
		return span ? windowAt(text, span[0], span[1]) : escapeHtml(text.slice(0, 140));
	}

	const results = $derived.by<Hit[]>(() => {
		const q = query.trim();
		if (q.length < 2) return [];
		const needle = normalizeForSearch(q, indexEnglish);
		const hits: Hit[] = [];
		for (const para of indexed) {
			if (para.norm.includes(needle)) {
				hits.push({
					order: para.order,
					title: para.title,
					p: para.p,
					snippet: snippetFor(para.text, q)
				});
				if (hits.length >= MAX_RESULTS) break;
			}
		}
		return hits;
	});

	// Build the index the first time the panel opens for this book. Split each
	// chapter's cleaned HTML into its top-level blocks — the same blocks the
	// reader indexes bookmarks and highlights against.
	async function buildIndex() {
		if (indexedSlug === slug && indexed.length) return;
		indexing = true;
		indexed = [];
		indexedSlug = slug;
		const lang = getLang();
		try {
			const book = await getBook(slug, lang);
			// Porter-stem only English editions (incl. en-modern); other scripts
			// are folded but never suffix-stripped.
			indexEnglish = (book.language || lang).startsWith('en');
			// Gated at six. An unbounded Promise.all fired one request per
			// chapter at once — 39 for Mawe ya Kukanyagia — from a drawer a
			// reader opens casually. That exceeds the browser's own connection
			// cap anyway, so the requests queued regardless; all it added was a
			// spike at the API proportional to book length. createLimiter exists
			// for exactly this and its docstring uses this shape as the example.
			const gate = createLimiter(6);
			const chapters = await Promise.all(
				book.chapters.map((c) =>
					gate(() => getChapter(slug, c.order, lang))
						.then((ch) => ({ order: c.order, title: c.title || `${c.order}`, html: ch.body_html }))
						.catch(() => null)
				)
			);
			const div = document.createElement('div');
			const paras: Para[] = [];
			for (const ch of chapters) {
				if (!ch) continue;
				div.innerHTML = ch.html;
				[...div.children].forEach((el, p) => {
					const text = (el.textContent ?? '').replace(/\s+/g, ' ').trim();
					if (text)
						paras.push({
							order: ch.order,
							title: ch.title,
							p,
							text,
							norm: normalizeForSearch(text, indexEnglish)
						});
				});
			}
			indexed = paras;
		} catch {
			indexedSlug = '';
		} finally {
			indexing = false;
		}
	}

	$effect(() => {
		if (!open) return;
		buildIndex();
		// Focus the query field; DrawerShell's focusTrap (autoFocus off) owns
		// keeping Tab inside the panel and returning focus to the opener on close.
		queueMicrotask(() => input?.focus());
	});

	function close() {
		open = false;
	}
</script>

<DrawerShell bind:open title={t('reader.search')} autoFocus={false}>
	{#snippet headerExtra()}
		<input
			bind:this={input}
			bind:value={query}
			type="search"
			class="field mt-3 w-full"
			placeholder={t('reader.searchPlaceholder')}
			aria-label={t('reader.searchPlaceholder')}
		/>
	{/snippet}

	<div class="search-list">
		{#if indexing}
			<p class="px-5 py-4 text-small text-muted">{t('search.indexing')}</p>
		{:else if query.trim().length < 2}
			<p class="px-5 py-4 text-small text-muted">{t('search.prompt')}</p>
		{:else if results.length === 0}
			<p class="px-5 py-4 text-small text-muted">{t('search.noResults')} “{query.trim()}”</p>
		{:else}
			<ul>
				{#each results as hit (hit.order + '-' + hit.p)}
					<li>
						<a
							href={localizeHref(`/books/${slug}/${hit.order}?p=${hit.p}`)}
							class="search-item"
							onclick={close}
						>
							<span class="eyebrow block text-muted">
								{chapterLabel(hit.order, hit.title)}
							</span>
							<!-- snippet is HTML-escaped by highlightAround ($lib/highlight); only <mark> is added -->
							<!-- eslint-disable-next-line svelte/no-at-html-tags -->
							<span class="mt-0.5 block text-small text-text">{@html hit.snippet}</span>
						</a>
					</li>
				{/each}
			</ul>
		{/if}

		<!-- The way up. Shown alongside hits as well as instead of them: this
		     search folds inflections of one root but not across roots, so a
		     short list is not proof there is nothing more — "praying" still
		     doesn't find "prayer" here, and does one rung up. -->
		{#if query.trim().length >= 2 && !indexing}
			<a
				href={localizeHref(scopedSearchHref('book', slug, query))}
				class="block px-5 py-4 text-small font-semibold text-accent hover:underline"
				onclick={close}
			>
				{t('search.wider')} →
			</a>
		{/if}
	</div>
</DrawerShell>

<style>
	.search-list {
		flex: 1;
		overflow-y: auto;
		padding: 0.25rem 0 1.5rem;
	}
	.search-item {
		display: block;
		padding: 0.6rem 1.25rem;
		text-decoration: none;
		border-bottom: 1px solid color-mix(in srgb, var(--border) 60%, transparent);
	}
	.search-item:hover {
		background: var(--surface-2);
	}
	.search-item :global(mark) {
		background: color-mix(in srgb, var(--gold) 34%, transparent);
		color: inherit;
		border-radius: 2px;
		padding: 0.05em 0.1em;
	}
</style>
