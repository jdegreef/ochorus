<script lang="ts">
	import Icon from '$lib/components/Icon.svelte';
	import DrawerShell from '$lib/components/DrawerShell.svelte';
	import { getBook, type BookDetail } from '$lib/library-public';
	import { getScrollAnchor } from '$lib/progress';
	import { marks } from '$lib/marks.svelte';
	import { bookmarks } from '$lib/bookmarks.svelte';
	import { removeBookmarkUndoable } from '$lib/undoable';
	import { undo } from '$lib/undo.svelte';
	import type { Bookmark } from '$lib/reading-schema';
	import { chapterLabel, editionLang, readingTime } from '$lib/reading';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';

	/**
	 * Slide-over table of contents for the reader. The book's chapter list is
	 * fetched lazily on first open (and served instantly thereafter via the
	 * service worker's cache). Shows the current chapter, chapters you've
	 * visited, and a small tally where you've left highlights or notes.
	 */
	let {
		slug,
		currentOrder,
		edition = null,
		open = $bindable(false)
	}: {
		slug: string;
		currentOrder: number;
		/** 'modern' keeps the TOC on the Modern English edition. */
		edition?: 'modern' | null;
		open?: boolean;
	} = $props();

	const t = i18n.t;
	let book = $state<BookDetail | null>(null);

	// Carry the reader's edition onto every chapter link (and fetch the matching
	// TOC titles) so tapping a chapter in the drawer stays in the same edition.
	const suffix = $derived(edition === 'modern' ? '?edition=modern' : '');
	const contentLang = $derived(editionLang(edition));
	// The fetched book, but only while it is THIS work: a drawer reopened on a
	// second book keeps the previous one in `book` until its replacement lands,
	// and chapter 3 of the wrong book is not chapter 3 of this one.
	//
	// Slug only — deliberately NOT the edition. `getBook` answers a modern-edition
	// request with the original when a book has no modern text (a silent 404
	// fallback, the same one the reader's own body takes), so gating the render on
	// the edition emptied the whole panel for every book without a modern edition.
	const loaded = $derived(book && book.slug === slug ? book : null);
	// What the current `book` was REQUESTED with, which is the only sound thing to
	// re-fetch on: asking "is what came back the edition I wanted?" never settles
	// for a book with no modern text — the fallback answers the same way forever,
	// and each reply is a new object, so the effect refetched in a loop.
	let fetchedKey = '';
	const wantKey = $derived(`${slug}\u0000${contentLang}`);
	// What to COUNT highlights against: the edition the API actually returned,
	// which is not always the one asked for (`getBook` falls back to English for
	// a book with no copy in this language). Counting the requested edition
	// would show a zero beside a chapter whose highlights are right there.
	const shownLang = $derived(loaded?.language ?? contentLang);

	$effect(() => {
		if (!open) return;
		bookmarks.load('book', slug);
		if (fetchedKey !== wantKey) {
			fetchedKey = wantKey;
			getBook(slug, contentLang)
				.then((b) => (book = b))
				// Clear the key too, so reopening the drawer retries rather than
				// sitting on a failure for the life of the page.
				.catch(() => ((book = null), (fetchedKey = '')));
		}
	});

	function close() {
		open = false;
	}

	// An Undo drawn in here loses its home when the drawer closes — by a link,
	// the shell's ✕, its scrim or Escape alike — so hand it to the corner toast
	// rather than throwing it away with the panel.
	$effect(() => {
		if (!open) undo.toToast();
	});

	const visited = (order: number) =>
		order === currentOrder || getScrollAnchor(slug, order) !== null;

	// A bookmark froze its chapter title at the moment it was saved, so a title
	// corrected since then (a redundant "1. " prefix stripped, a typo fixed) left
	// the bookmark quoting the old text — directly above the contents list showing
	// the new one. Read the live title instead, and keep the snapshot as the
	// fallback: it is all there is before the book loads, and offline.
	const titleOf = (bm: Bookmark) =>
		loaded?.chapters.find((c) => c.order === bm.order)?.title || bm.title;
</script>

<DrawerShell bind:open ariaLabel={t('reader.contents')} width="min(22rem, 88vw)">
	{#snippet titleArea()}
		<div class="min-w-0">
			<h2 class="truncate text-h3 text-text">{loaded?.title ?? t('reader.contents')}</h2>
			{#if loaded}
				<p class="text-small text-muted">{loaded.author.name}</p>
			{/if}
		</div>
	{/snippet}

	<nav class="toc-list" aria-label={t('reader.contents')}>
		{#if bookmarks.list.length}
			<div class="bm-section">
				<p class="bm-heading eyebrow">🔖 {t('reader.bookmarks')}</p>
				<ul>
					{#each bookmarks.list as bm (bm.id)}
						{@const title = titleOf(bm)}
						<li class="bm-row">
							<a
								href={localizeHref(
									`/books/${slug}/${bm.order}?p=${bm.p}${edition === 'modern' ? '&edition=modern' : ''}`
								)}
								class="toc-item min-w-0 flex-1"
								onclick={close}
							>
								<span class="min-w-0 flex-1">
									<span class="block truncate text-small text-text">{bm.snippet || title}</span>
									<span class="block text-micro text-muted">{chapterLabel(bm.order, title)}</span>
								</span>
							</a>
							<button
								class="bm-remove"
								onclick={() => removeBookmarkUndoable(bm.id, { inline: true })}
								aria-label={t('reader.bookmark')}><Icon name="close" size={14} /></button
							>
						</li>
					{/each}
				</ul>
			</div>
		{/if}
		<!-- The Undo for a bookmark removed just above, drawn INSIDE the dialog:
		     the shell is aria-modal with a focus trap, so the corner toast that
		     carries every other Undo is out of a keyboard's and a screen reader's
		     reach here. Outside the bookmarks block, because removing the last
		     bookmark makes that block disappear. -->
		{#if undo.current?.inline}
			<p class="bm-undo" role="status">
				<span class="text-small text-muted">{t('undo.removed')}</span>
				<button class="bm-undo-btn" onclick={() => undo.act()}>{t('undo.action')}</button>
			</p>
		{/if}
		{#if !loaded}
			<p class="px-5 py-4 text-small text-muted">…</p>
		{:else}
			<ol>
				{#each loaded.chapters as ch (ch.order)}
					{@const markCount = marks.countFor(slug, ch.order, 'book', shownLang)}
					<li>
						<a
							href={localizeHref(`/books/${slug}/${ch.order}${suffix}`)}
							class="toc-item"
							class:current={ch.order === currentOrder}
							aria-current={ch.order === currentOrder ? 'page' : undefined}
							onclick={close}
						>
							<span
								class="toc-dot"
								class:on={visited(ch.order)}
								aria-hidden="true"
							></span>
							<span class="min-w-0 flex-1">
								<span class="block truncate text-small text-text">
									{chapterLabel(ch.order, ch.title)}
								</span>
								<span class="block text-micro text-muted">
									{readingTime(ch.word_count)}{#if markCount > 0}
										· {markCount} {markCount === 1 ? t('reader.markOne') : t('reader.markMany')}{/if}
								</span>
							</span>
						</a>
					</li>
				{/each}
			</ol>
		{/if}
	</nav>
</DrawerShell>

<style>
	.toc-list {
		flex: 1;
		overflow-y: auto;
		padding: 0.5rem 0 1.5rem;
	}
	.toc-item {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.55rem 1.25rem;
		text-decoration: none;
	}
	.toc-item:hover {
		background: var(--surface-2);
	}
	.bm-section {
		border-bottom: 1px solid var(--border);
		padding-bottom: 0.5rem;
		margin-bottom: 0.25rem;
	}
	.bm-heading {
		padding: 0.75rem 1.25rem 0.25rem;
		font-size: var(--fs-micro);
		color: var(--muted);
	}
	.bm-row {
		display: flex;
		align-items: center;
	}
	.bm-remove {
		flex-shrink: 0;
		padding: 0.4rem 1rem 0.4rem 0.4rem;
		color: var(--muted);
		background: none;
		border: none;
		cursor: pointer;
	}
	.bm-remove:hover {
		color: var(--text);
	}
	.bm-undo {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.5rem 1.25rem;
		border-bottom: 1px solid var(--border);
	}
	.bm-undo-btn {
		border-radius: 999px;
		background: var(--accent);
		color: var(--accent-contrast);
		padding: 0.2rem 0.7rem;
		font-weight: 600;
		font-size: var(--fs-small);
	}
	.toc-item.current {
		background: color-mix(in srgb, var(--accent) 8%, transparent);
		border-inline-end: 3px solid var(--accent);
	}
	.toc-dot {
		width: 0.45rem;
		height: 0.45rem;
		flex-shrink: 0;
		border-radius: 999px;
		border: 1px solid var(--border);
	}
	.toc-dot.on {
		background: var(--accent);
		border-color: var(--accent);
	}
</style>
