<script lang="ts">
	import { focusTrap } from '$lib/actions/focusTrap';
	import { getBook, getChapter } from '$lib/library';
	import { getLang } from '$lib/lang.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { highlightAround } from '$lib/highlight';
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
	 * It matches **literal substrings**, which is what makes it work offline and
	 * land on the exact paragraph — but it means "praying" does not find
	 * "prayer". So every state offers the way up to the server's search of the
	 * same book (`/search?in=book:…`), which stems and ranks; from there one
	 * click widens to the whole library. Device → book → library, and the reader
	 * can always see which rung they are on.
	 */
	let {
		slug,
		open = $bindable(false)
	}: {
		slug: string;
		open?: boolean;
	} = $props();

	const t = i18n.t;

	type Para = { order: number; title: string; p: number; text: string };
	type Hit = { order: number; title: string; p: number; snippet: string };

	let input = $state<HTMLInputElement>();

	// The flattened paragraph index for the loaded book, and which book it's for.
	let indexed = $state<Para[]>([]);
	let indexedSlug = '';
	let indexing = $state(false);

	let query = $state('');
	const MAX_RESULTS = 80;

	const results = $derived.by<Hit[]>(() => {
		const q = query.trim();
		if (q.length < 2) return [];
		const needle = q.toLowerCase();
		const hits: Hit[] = [];
		for (const para of indexed) {
			if (para.text.toLowerCase().includes(needle)) {
				hits.push({
				order: para.order,
				title: para.title,
				p: para.p,
				snippet: highlightAround(para.text, q)
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
			const chapters = await Promise.all(
				book.chapters.map((c) =>
					getChapter(slug, c.order, lang)
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
					if (text) paras.push({ order: ch.order, title: ch.title, p, text });
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
		// Focus the query field; focusTrap on the panel owns keeping Tab inside it
		// and returning focus to the opener on close.
		queueMicrotask(() => input?.focus());
	});

	function close() {
		open = false;
	}

	function onKeydown(e: KeyboardEvent) {
		if (!open) return;
		if (e.key === 'Escape') {
			e.stopPropagation();
			close();
		}
	}
</script>

<svelte:window onkeydown={onKeydown} />

{#if open}
	<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
	<div class="search-scrim" onclick={close}></div>
	<!-- focusTrap keeps Tab inside the panel. Without it this dialog declared
	     aria-modal="true" — telling assistive tech the rest of the page is inert
	     — while Tab actually walked straight out into the content behind the
	     scrim. autoFocus is off because the effect above focuses the input
	     itself. Escape has two paths on purpose: the trap handles it (and stops
	     propagation) whenever focus is inside the panel, and the window listener
	     still catches it if focus has fallen elsewhere, e.g. after a scrim click. -->
	<div
		class="search-panel"
		role="dialog"
		aria-modal="true"
		aria-label={t('reader.search')}
		use:focusTrap={{ onEscape: close, autoFocus: false }}
	>
		<header class="border-b border-border px-5 py-4">
			<div class="flex items-center justify-between gap-3">
				<h2 class="text-h3 text-text">{t('reader.search')}</h2>
				<button class="btn btn-ghost !px-2.5 !py-1" onclick={close} aria-label={t('a11y.close')}>✕</button>
			</div>
			<input
				bind:this={input}
				bind:value={query}
				type="search"
				class="mt-3 w-full rounded-sm border border-border-strong bg-bg px-3 py-2 text-body text-text"
				placeholder={t('reader.searchPlaceholder')}
				aria-label={t('reader.searchPlaceholder')}
			/>
		</header>

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
								<span class="block text-[0.72rem] uppercase tracking-wide text-muted">
									{hit.order}. {hit.title}
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
			     search matches literal substrings, so a short list is not proof
			     there is nothing more — "praying" simply doesn't find "prayer"
			     here, and does one rung up. -->
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
	</div>
{/if}

<style>
	.search-scrim {
		position: fixed;
		inset: 0;
		z-index: 48;
		background: rgb(0 0 0 / 0.35);
	}
	.search-panel {
		position: fixed;
		top: 0;
		bottom: 0;
		/* Anchored to the end of the reading direction — the left edge under
		   dir="rtl". See the matching note in TocDrawer: box-shadow and
		   translateX have no logical form, so they are flipped explicitly. */
		inset-inline-end: 0;
		z-index: 49;
		width: min(24rem, 92vw);
		display: flex;
		flex-direction: column;
		background: var(--surface);
		border-inline-start: 1px solid var(--border);
		box-shadow: var(--shadow-drawer);
		--search-slide-from: 1.5rem;
		animation: search-in var(--duration-fast) ease-out;
	}
	:global([dir='rtl']) .search-panel {
		box-shadow: 12px 0 40px rgb(0 0 0 / 0.25);
		--search-slide-from: -1.5rem;
	}
	@keyframes search-in {
		from {
			transform: translateX(var(--search-slide-from, 1.5rem));
			opacity: 0;
		}
	}
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
