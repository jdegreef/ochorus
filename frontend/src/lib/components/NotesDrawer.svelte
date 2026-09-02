<script lang="ts">
	import { getBook, getChapter } from '$lib/library-public';
	import { marks } from '$lib/marks.svelte';
	import { createLimiter, NOTEBOOK_CONCURRENCY } from '$lib/limiter';
	import { paragraphs, groupMarks, type Highlight } from '$lib/markText';
	import { editionLang, chapterLabel } from '$lib/reading';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';

	/**
	 * In-reader notes & highlights for the CURRENT book — a study surface without
	 * leaving the page. It re-fetches each chapter that carries a mark (gated,
	 * served from the service-worker cache after first read) to quote the
	 * highlighted text, then groups them by chapter with a jump to `?p=`. The
	 * whole-library equivalent is `/notebook`; both share `$lib/markText`.
	 */
	let {
		slug,
		edition = null,
		open = $bindable(false)
	}: {
		slug: string;
		/** 'modern' keeps the drawer on the Modern English edition's marks. */
		edition?: 'modern' | null;
		open?: boolean;
	} = $props();

	const t = i18n.t;
	const contentLang = $derived(editionLang(edition));

	type ChapterNotes = { order: number; title: string; highlights: Highlight[] };
	let blocks = $state<ChapterNotes[]>([]);
	let loading = $state(false);
	let panel = $state<HTMLElement>();
	let opener: Element | null = null;
	// Supersede an in-flight build when the book/edition changes under an open
	// drawer (toggling Modern↔Original re-fires the effect): only the latest
	// build assigns `blocks`/`loading`, so a slow fetch for the previous edition
	// can't overwrite the current one's quotes (and their edition links).
	let buildToken = 0;

	async function build() {
		const token = ++buildToken;
		// Marks for THIS book in the current edition, grouped by chapter.
		const mine = marks
			.all(contentLang)
			.filter((w) => w.kind === 'book' && w.slug === slug)
			.sort((a, b) => a.order - b.order);
		if (!mine.length) {
			if (token === buildToken) blocks = [];
			return;
		}
		loading = true;
		try {
			const book = await getBook(slug, contentLang).catch(() => null);
			const titleOf = (order: number) =>
				book?.chapters.find((c) => c.order === order)?.title ?? '';
			const gate = createLimiter(NOTEBOOK_CONCURRENCY);
			const built = await Promise.all(
				mine.map((w) =>
					gate(() => getChapter(slug, w.order, contentLang))
						.then((ch) => ({
							order: w.order,
							title: titleOf(w.order),
							highlights: groupMarks(paragraphs(ch.body_html), w.marks, contentLang)
						}))
						.catch(() => null)
				)
			);
			if (token !== buildToken) return; // a newer build superseded this one
			blocks = built.filter(
				(b): b is ChapterNotes => b !== null && b.highlights.length > 0
			);
		} finally {
			if (token === buildToken) loading = false;
		}
	}

	$effect(() => {
		if (!open) return;
		opener = document.activeElement;
		// Rebuild each open — marks may have changed since last time (and the
		// chapter fetches are service-worker-cached, so a reopen is cheap).
		build();
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
		// Simple focus trap: keep Tab cycling inside the panel (as TocDrawer).
		if (e.key === 'Tab' && panel) {
			const f = panel.querySelectorAll<HTMLElement>('a[href], button:not([disabled])');
			if (!f.length) return;
			const first = f[0];
			const last = f[f.length - 1];
			if (e.shiftKey && document.activeElement === first) {
				e.preventDefault();
				last.focus();
			} else if (!e.shiftKey && document.activeElement === last) {
				e.preventDefault();
				first.focus();
			}
		}
	}
</script>

<svelte:window onkeydown={onKeydown} />

{#if open}
	<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
	<div class="notes-scrim" onclick={close}></div>
	<div
		bind:this={panel}
		class="notes-panel"
		role="dialog"
		aria-modal="true"
		aria-label={t('notebook.title')}
	>
		<header class="flex items-center justify-between gap-3 border-b border-border px-5 py-4">
			<h2 class="text-h3 text-text">{t('notebook.title')}</h2>
			<button class="btn btn-icon btn-ghost" onclick={close} aria-label={t('a11y.close')}>✕</button>
		</header>

		<div class="notes-list">
			{#if loading}
				<p class="px-5 py-4 text-small text-muted">…</p>
			{:else if blocks.length === 0}
				<p class="px-5 py-6 text-small text-muted">{t('notebook.empty')}</p>
			{:else}
				{#each blocks as ch (ch.order)}
					<div class="ch-group">
						<p class="ch-heading eyebrow">{chapterLabel(ch.order, ch.title)}</p>
						<ul>
							{#each ch.highlights as hl (hl.id)}
								<li>
									<a
										href={localizeHref(
											`/books/${slug}/${ch.order}?p=${hl.p}${edition === 'modern' ? '&edition=modern' : ''}`
										)}
										class="hl-item"
										style="border-inline-start-color: var(--hl-{hl.color})"
										onclick={close}
									>
										{#if hl.text}
											<span class="block text-small italic text-text">“{hl.text}”</span>
										{/if}
										{#if hl.note}
											<span class="mt-1 block text-micro text-muted">📝 {hl.note}</span>
										{/if}
									</a>
								</li>
							{/each}
						</ul>
					</div>
				{/each}
			{/if}
		</div>
	</div>
{/if}

<style>
	.notes-scrim {
		position: fixed;
		inset: 0;
		z-index: 48;
		background: rgb(0 0 0 / 0.35);
	}
	.notes-panel {
		position: fixed;
		top: 0;
		bottom: 0;
		/* End of the reading direction (left edge under RTL) — see TocDrawer. */
		inset-inline-end: 0;
		z-index: 49;
		width: min(24rem, 92vw);
		display: flex;
		flex-direction: column;
		background: var(--surface);
		border-inline-start: 1px solid var(--border);
		box-shadow: var(--shadow-drawer);
		--notes-slide-from: 1.5rem;
		animation: notes-in var(--duration-fast) ease-out;
	}
	:global([dir='rtl']) .notes-panel {
		box-shadow: 12px 0 40px rgb(0 0 0 / 0.25);
		--notes-slide-from: -1.5rem;
	}
	@keyframes notes-in {
		from {
			transform: translateX(var(--notes-slide-from, 1.5rem));
			opacity: 0;
		}
	}
	.notes-list {
		flex: 1;
		overflow-y: auto;
		padding: 0.25rem 0 1.5rem;
	}
	.ch-group {
		border-bottom: 1px solid color-mix(in srgb, var(--border) 60%, transparent);
		padding-bottom: 0.5rem;
	}
	.ch-heading {
		padding: 0.75rem 1.25rem 0.35rem;
		font-size: var(--fs-micro);
		color: var(--muted);
	}
	.hl-item {
		display: block;
		padding: 0.5rem 1.25rem;
		margin-inline-start: 1.25rem;
		border-inline-start: 3px solid var(--border);
		text-decoration: none;
	}
	.hl-item:hover {
		background: var(--surface-2);
	}
</style>
