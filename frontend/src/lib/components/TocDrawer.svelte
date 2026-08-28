<script lang="ts">
	import Icon from '$lib/components/Icon.svelte';
	import { getBook, type BookDetail } from '$lib/library-public';
	import { getScrollAnchor } from '$lib/progress';
	import { marks } from '$lib/marks.svelte';
	import { bookmarks } from '$lib/bookmarks.svelte';
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
	let panel = $state<HTMLElement>();
	let opener: Element | null = null;

	// Carry the reader's edition onto every chapter link (and fetch the matching
	// TOC titles) so tapping a chapter in the drawer stays in the same edition.
	const suffix = $derived(edition === 'modern' ? '?edition=modern' : '');
	const contentLang = $derived(editionLang(edition));
	// What to COUNT highlights against: the edition the API actually returned,
	// which is not always the one asked for (`getBook` falls back to English for
	// a book with no copy in this language). Counting the requested edition
	// would show a zero beside a chapter whose highlights are right there.
	const shownLang = $derived(book?.language ?? contentLang);

	$effect(() => {
		if (!open) return;
		opener = document.activeElement;
		bookmarks.load('book', slug);
		if (!book || book.slug !== slug || book.is_modern_edition !== (edition === 'modern')) {
			getBook(slug, contentLang)
				.then((b) => (book = b))
				.catch(() => (book = null));
		}
		// Focus the panel once it renders.
		queueMicrotask(() => panel?.querySelector<HTMLElement>('a, button')?.focus());
		return () => {
			(opener as HTMLElement | null)?.focus?.();
		};
	});

	function close() {
		open = false;
	}

	function onKeydown(e: KeyboardEvent) {
		if (!open) return;
		if (e.key === 'Escape') {
			e.stopPropagation();
			close();
			return;
		}
		// Simple focus trap: keep Tab cycling inside the panel.
		if (e.key === 'Tab' && panel) {
			const focusables = panel.querySelectorAll<HTMLElement>(
				'a[href], button:not([disabled])'
			);
			if (!focusables.length) return;
			const first = focusables[0];
			const last = focusables[focusables.length - 1];
			if (e.shiftKey && document.activeElement === first) {
				e.preventDefault();
				last.focus();
			} else if (!e.shiftKey && document.activeElement === last) {
				e.preventDefault();
				first.focus();
			}
		}
	}

	const visited = (order: number) =>
		order === currentOrder || getScrollAnchor(slug, order) !== null;
</script>

<svelte:window onkeydown={onKeydown} />

{#if open}
	<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
	<div class="toc-scrim" onclick={close}></div>
	<div
		bind:this={panel}
		class="toc-panel"
		role="dialog"
		aria-modal="true"
		aria-label={t('reader.contents')}
	>
		<header class="flex items-center justify-between gap-3 border-b border-border px-5 py-4">
			<div class="min-w-0">
				<h2 class="truncate text-h3 text-text">{book?.title ?? t('reader.contents')}</h2>
				{#if book}
					<p class="text-small text-muted">{book.author.name}</p>
				{/if}
			</div>
			<button class="btn btn-icon btn-ghost" onclick={close} aria-label={t('a11y.close')}>✕</button>
		</header>

		<nav class="toc-list" aria-label={t('reader.contents')}>
			{#if bookmarks.list.length}
				<div class="bm-section">
					<p class="bm-heading eyebrow">🔖 {t('reader.bookmarks')}</p>
					<ul>
						{#each bookmarks.list as bm (bm.id)}
							<li class="bm-row">
								<a
									href={localizeHref(
										`/books/${slug}/${bm.order}?p=${bm.p}${edition === 'modern' ? '&edition=modern' : ''}`
									)}
									class="toc-item min-w-0 flex-1"
									onclick={close}
								>
									<span class="min-w-0 flex-1">
										<span class="block truncate text-small text-text">{bm.snippet || bm.title}</span>
										<span class="block text-micro text-muted">{chapterLabel(bm.order, bm.title)}</span>
									</span>
								</a>
								<button
									class="bm-remove"
									onclick={() => bookmarks.remove(bm.id)}
									aria-label={t('reader.bookmark')}><Icon name="close" size={14} /></button
								>
							</li>
						{/each}
					</ul>
				</div>
			{/if}
			{#if !book}
				<p class="px-5 py-4 text-small text-muted">…</p>
			{:else}
				<ol>
					{#each book.chapters as ch (ch.order)}
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
	</div>
{/if}

<style>
	.toc-scrim {
		position: fixed;
		inset: 0;
		z-index: 48;
		background: rgb(0 0 0 / 0.35);
	}
	.toc-panel {
		position: fixed;
		top: 0;
		bottom: 0;
		/* The drawer belongs at the END of the reading direction, which under
		   dir="rtl" (Arabic) is the LEFT edge — so it is anchored, bordered and
		   slid logically. Box-shadow offsets and translateX have no logical
		   form, so those two are flipped explicitly below; everything else
		   follows the inline axis on its own. */
		inset-inline-end: 0;
		z-index: 49;
		width: min(22rem, 88vw);
		display: flex;
		flex-direction: column;
		background: var(--surface);
		border-inline-start: 1px solid var(--border);
		box-shadow: var(--shadow-drawer);
		--toc-slide-from: 1.5rem;
		animation: toc-in var(--duration-fast) ease-out;
	}
	:global([dir='rtl']) .toc-panel {
		box-shadow: 12px 0 40px rgb(0 0 0 / 0.25);
		--toc-slide-from: -1.5rem;
	}
	@keyframes toc-in {
		from {
			transform: translateX(var(--toc-slide-from, 1.5rem));
			opacity: 0;
		}
	}
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
