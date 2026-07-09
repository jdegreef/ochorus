<script lang="ts">
	import { getBook, type BookDetail } from '$lib/library';
	import { getLang } from '$lib/lang.svelte';
	import { getScrollAnchor } from '$lib/progress';
	import { marks } from '$lib/marks.svelte';
	import { readingTime } from '$lib/reading';
	import { i18n } from '$lib/i18n.svelte';

	/**
	 * Slide-over table of contents for the reader. The book's chapter list is
	 * fetched lazily on first open (and served instantly thereafter via the
	 * service worker's cache). Shows the current chapter, chapters you've
	 * visited, and a small tally where you've left highlights or notes.
	 */
	let {
		slug,
		currentOrder,
		open = $bindable(false)
	}: {
		slug: string;
		currentOrder: number;
		open?: boolean;
	} = $props();

	const t = i18n.t;
	let book = $state<BookDetail | null>(null);
	let panel = $state<HTMLElement>();
	let opener: Element | null = null;

	$effect(() => {
		if (!open) return;
		opener = document.activeElement;
		if (!book || book.slug !== slug) {
			getBook(slug, getLang())
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
			<button class="btn btn-ghost !px-2.5 !py-1" onclick={close} aria-label="Close">✕</button>
		</header>

		<nav class="toc-list" aria-label={t('reader.contents')}>
			{#if !book}
				<p class="px-5 py-4 text-small text-muted">…</p>
			{:else}
				<ol>
					{#each book.chapters as ch (ch.order)}
						{@const markCount = marks.countFor(slug, ch.order)}
						<li>
							<a
								href="/books/{slug}/{ch.order}"
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
										{ch.order}. {ch.title || `${t('plans.day')} ${ch.order}`}
									</span>
									<span class="block text-[0.72rem] text-muted">
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
		right: 0;
		bottom: 0;
		z-index: 49;
		width: min(22rem, 88vw);
		display: flex;
		flex-direction: column;
		background: var(--surface);
		border-left: 1px solid var(--border);
		box-shadow: -12px 0 40px rgb(0 0 0 / 0.25);
		animation: toc-in 0.18s ease-out;
	}
	@keyframes toc-in {
		from {
			transform: translateX(1.5rem);
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
	.toc-item.current {
		background: color-mix(in srgb, var(--accent) 8%, transparent);
		border-right: 3px solid var(--accent);
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
