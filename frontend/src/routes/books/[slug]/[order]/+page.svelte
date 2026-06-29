<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { page } from '$app/stores';
	import type { Chapter } from '$lib/library';
	import { saveProgress, getScrollAnchor, saveScrollAnchor } from '$lib/progress';
	import { readerPrefs } from '$lib/readerPrefs.svelte';
	import { readerUi } from '$lib/readerUi.svelte';
	import { marks } from '$lib/marks.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { readingTime } from '$lib/reading';
	import ReaderControls from '$lib/components/ReaderControls.svelte';
	import SelectionBar from '$lib/components/SelectionBar.svelte';

	let { data } = $props();
	const chapter = $derived(data.chapter as Chapter);
	const slug = $derived(data.slug as string);
	const t = i18n.t;

	let body: HTMLDivElement | undefined = $state();
	let titleEl: HTMLHeadingElement | undefined = $state();
	let titleVisible = $state(true);

	// Note editor state.
	let noteOpen = $state(false);
	let noteIndex = $state(-1);
	let noteDraft = $state('');

	const HEADER_OFFSET = 72;

	onMount(() => {
		readerPrefs.init();
	});

	// Per-chapter setup: progress, marks, restore scroll, observe title.
	$effect(() => {
		const s = slug;
		const order = chapter.order;
		saveProgress(s, order);
		marks.load(s, order);

		let cleanup: (() => void) | undefined;
		(async () => {
			await tick();
			restoreScroll(s, order);
			cleanup = observeTitle();
		})();
		return () => cleanup?.();
	});

	function restoreScroll(s: string, order: number) {
		const idx = getScrollAnchor(s, order);
		if (idx && body && body.children[idx]) {
			body.children[idx].scrollIntoView({ block: 'start' });
			window.scrollBy(0, -HEADER_OFFSET);
		} else {
			window.scrollTo(0, 0);
		}
	}

	// Throttled save of the topmost visible paragraph as the scroll anchor.
	let saveTimer: ReturnType<typeof setTimeout> | undefined;
	function onScroll() {
		clearTimeout(saveTimer);
		saveTimer = setTimeout(() => {
			if (!body) return;
			const kids = body.children;
			let topIndex = 0;
			for (let i = 0; i < kids.length; i++) {
				if (kids[i].getBoundingClientRect().top >= HEADER_OFFSET) {
					topIndex = Math.max(0, i - 1);
					break;
				}
			}
			saveScrollAnchor(slug, chapter.order, topIndex);
		}, 250);
	}

	function observeTitle(): () => void {
		if (!titleEl) return () => {};
		const io = new IntersectionObserver(([e]) => (titleVisible = e.isIntersecting), {
			rootMargin: `-${HEADER_OFFSET}px 0px 0px 0px`
		});
		io.observe(titleEl);
		return () => io.disconnect();
	}

	// Decorate rendered paragraphs with highlight backgrounds + note markers.
	$effect(() => {
		const hl = marks.highlights;
		const notes = marks.notes;
		if (!body) return;
		const kids = body.children;
		for (let i = 0; i < kids.length; i++) {
			const el = kids[i] as HTMLElement;
			el.classList.toggle('mark-hl', hl.has(i));
			el.classList.toggle('mark-note', notes[i] != null);
		}
	});

	const cite = $derived({
		author: chapter.author_name,
		book: chapter.book_title,
		chapter: chapter.title,
		url: $page.url.href
	});

	function openNote(i: number) {
		noteIndex = i;
		noteDraft = marks.getNote(i);
		noteOpen = true;
	}
	function saveNote() {
		marks.setNote(noteIndex, noteDraft);
		noteOpen = false;
	}
</script>

<svelte:head><title>{chapter.title} — {chapter.book_title} — Ochorus</title></svelte:head>
<svelte:window onscroll={onScroll} />

<!-- Reader top bar: breadcrumb / context + controls. Hidden in focus mode. -->
{#if !readerUi.focus}
	<div class="sticky top-0 z-10 border-b border-border bg-bg/90 backdrop-blur">
		<div class="mx-auto flex max-w-3xl items-center justify-between gap-3 px-5 py-2.5">
			<div class="min-w-0 flex-1">
				{#if titleVisible}
					<a href="/books/{slug}" class="text-small text-muted hover:text-text">
						← {chapter.book_title}
					</a>
				{:else}
					<!-- Once the heading scrolls away, show where you are. -->
					<div class="truncate text-small text-text">
						<span class="text-muted">{chapter.book_title} · </span>{chapter.title}
					</div>
				{/if}
			</div>
			<div class="flex shrink-0 items-center gap-1">
				{#if chapter.prev}
					<a
						href="/books/{slug}/{chapter.prev.order}"
						class="btn btn-ghost !px-2.5 !py-1"
						aria-label={t('reader.previous')}>‹</a
					>
				{/if}
				{#if chapter.next}
					<a
						href="/books/{slug}/{chapter.next.order}"
						class="btn btn-ghost !px-2.5 !py-1"
						aria-label={t('reader.next')}>›</a
					>
				{/if}
				<ReaderControls />
				<button
					class="btn btn-ghost !px-3 !py-1"
					onclick={() => readerUi.toggleFocus()}
					aria-label={t('reader.focus')}
					title={t('reader.focus')}>☾</button
				>
			</div>
		</div>
	</div>
{/if}

{#if readerUi.focus}
	<button
		class="fixed right-4 top-4 z-30 rounded-full border border-border bg-surface/90 px-3 py-1.5 text-small text-muted shadow-md backdrop-blur hover:text-text"
		onclick={() => readerUi.exitFocus()}>✕ {t('reader.exitFocus')}</button
	>
{/if}

<article
	class="mx-auto px-5 py-10"
	style="{readerPrefs.style}; max-width: var(--reading-measure)"
	dir="auto"
>
	<!-- Breadcrumb -->
	<nav class="mb-5 flex flex-wrap items-center gap-1.5 text-small text-muted" aria-label="Breadcrumb">
		<a href="/books" class="hover:text-text">{t('nav.books')}</a>
		<span>›</span>
		<a href="/biographies#{chapter.author_slug}" class="hover:text-text">{chapter.author_name}</a>
		<span>›</span>
		<a href="/books/{slug}" class="hover:text-text">{chapter.book_title}</a>
	</nav>

	<p class="mb-1 text-small uppercase tracking-wider text-muted">
		Chapter {chapter.order} · {readingTime(chapter.word_count)}
	</p>
	<h1 bind:this={titleEl} class="text-h1 mb-8">{chapter.title}</h1>

	<!-- Body HTML is cleaned server-side to a safe tag subset on ingest. -->
	<div class="reading" bind:this={body}>{@html chapter.body_html}</div>

	<nav class="mt-14 flex items-stretch justify-between gap-3 border-t border-border pt-6">
		{#if chapter.prev}
			<a
				href="/books/{slug}/{chapter.prev.order}"
				class="btn btn-ghost flex-1 !flex-col !items-start gap-0.5 text-left"
			>
				<span class="text-[0.7rem] uppercase tracking-wider text-muted">{t('reader.previous')}</span>
				<span class="text-small">{chapter.prev.title}</span>
			</a>
		{:else}
			<span class="flex-1"></span>
		{/if}
		{#if chapter.next}
			<a
				href="/books/{slug}/{chapter.next.order}"
				class="btn btn-primary flex-1 !flex-col !items-end gap-0.5 text-right"
			>
				<span class="text-[0.7rem] uppercase tracking-wider opacity-75">{t('reader.next')}</span>
				<span class="text-small">{chapter.next.title}</span>
			</a>
		{:else}
			<a href="/books/{slug}" class="btn btn-ghost flex-1 text-center">{t('reader.backToContents')}</a>
		{/if}
	</nav>
</article>

<SelectionBar
	container={body}
	{cite}
	onHighlight={(i) => marks.toggleHighlight(i)}
	onNote={openNote}
	isHighlighted={(i) => marks.isHighlighted(i)}
/>

{#if noteOpen}
	<div class="note-overlay" role="dialog" aria-modal="true" aria-label={t('reader.note')}>
		<div class="note-card">
			<h2 class="mb-2 text-h3">{t('reader.note')}</h2>
			<textarea
				bind:value={noteDraft}
				rows="5"
				class="w-full rounded-sm border border-border bg-bg p-3 text-body text-text"
				placeholder="…"
			></textarea>
			<div class="mt-3 flex justify-end gap-2">
				<button class="btn btn-ghost" onclick={() => (noteOpen = false)}>Cancel</button>
				<button class="btn btn-primary" onclick={saveNote}>Save</button>
			</div>
		</div>
	</div>
{/if}

<style>
	/* Paragraph-level marks decorate {@html} children imperatively. */
	:global(.reading > .mark-hl) {
		background: color-mix(in srgb, var(--gold) 22%, transparent);
		border-radius: 4px;
		box-shadow: 0 0 0 4px color-mix(in srgb, var(--gold) 22%, transparent);
	}
	:global(.reading > .mark-note) {
		border-left: 3px solid var(--gold);
		padding-left: 0.9em;
		margin-left: -1.2em;
	}
	.note-overlay {
		position: fixed;
		inset: 0;
		z-index: 50;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 1rem;
		background: rgb(0 0 0 / 0.4);
	}
	.note-card {
		width: 100%;
		max-width: 32rem;
		border-radius: var(--radius-card);
		border: 1px solid var(--border);
		background: var(--surface);
		padding: 1.25rem;
		box-shadow: 0 10px 40px rgb(0 0 0 / 0.35);
	}
</style>
