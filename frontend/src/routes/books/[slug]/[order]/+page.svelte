<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { getPlan, type Chapter, type PlanDetail } from '$lib/library';
	import { planProgress } from '$lib/planProgress.svelte';
	import {
		saveProgress,
		getScrollAnchor,
		saveScrollAnchor,
		getProgressRecord
	} from '$lib/progress';
	import { readerPrefs } from '$lib/readerPrefs.svelte';
	import { readerUi } from '$lib/readerUi.svelte';
	import { marks } from '$lib/marks.svelte';
	import { renderMarks } from '$lib/rangeMarks';
	import { i18n } from '$lib/i18n.svelte';
	import { getLang } from '$lib/lang.svelte';
	import { readingTime } from '$lib/reading';
	import { listen } from '$lib/listen.svelte';
	import { define } from '$lib/define.svelte';
	import { API_BASE_URL } from '$lib/config';
	import ReaderControls from '$lib/components/ReaderControls.svelte';
	import DefinePopover from '$lib/components/DefinePopover.svelte';
	import TocDrawer from '$lib/components/TocDrawer.svelte';
	import SelectionBar from '$lib/components/SelectionBar.svelte';
	import ListenBar from '$lib/components/ListenBar.svelte';

	let { data } = $props();
	const chapter = $derived(data.chapter as Chapter);
	const slug = $derived(data.slug as string);
	const t = i18n.t;

	let body: HTMLDivElement | undefined = $state();
	let titleEl: HTMLHeadingElement | undefined = $state();
	let titleVisible = $state(true);

	// Note editor state — edits the note of an existing mark group, or creates
	// a new mark from pending selection segments when noteId is null.
	let noteOpen = $state(false);
	let noteId = $state<string | null>(null);
	let notePending = $state<{ p: number; s: number; e: number }[]>([]);
	let noteDraft = $state('');

	const HEADER_OFFSET = 72;
	let tocOpen = $state(false);

	onMount(() => {
		readerPrefs.init();
		listen.init();
	});

	// Per-chapter setup: progress, marks, restore scroll, observe title.
	$effect(() => {
		const s = slug;
		const order = chapter.order;
		const language = getLang();
		saveProgress(s, order, language);
		marks.load(s, order, language);

		let cleanup: (() => void) | undefined;
		(async () => {
			await tick();
			restoreScroll(s, order);
			cleanup = observeTitle();
		})();
		return () => cleanup?.();
	});

	// A first-sign-in sync can replace the local cache underneath us — re-read the
	// current chapter's marks so freshly-pulled highlights/notes appear.
	onMount(() => {
		const onSync = () => marks.refresh();
		window.addEventListener('ochorus:sync', onSync);
		return () => window.removeEventListener('ochorus:sync', onSync);
	});

	// Listen mode: stop speech when the chapter changes or the reader unmounts.
	$effect(() => {
		void slug;
		void chapter.order;
		return () => listen.stop();
	});

	function gotoChapter(target: { order: number } | null) {
		if (target) goto(`/books/${slug}/${target.order}`);
	}

	/** Keyboard: ←/→ chapters (or paragraph skip while listening), space pages. */
	function onKeydown(e: KeyboardEvent) {
		if (e.metaKey || e.ctrlKey || e.altKey) return;
		const el = e.target as HTMLElement;
		if (
			el?.closest?.('input, textarea, select, [contenteditable="true"]') ||
			noteOpen ||
			define.open ||
			tocOpen
		) {
			return;
		}
		if (e.key === 'ArrowRight') {
			e.preventDefault();
			if (listen.status !== 'idle') listen.skip(1);
			else gotoChapter(chapter.next);
		} else if (e.key === 'ArrowLeft') {
			e.preventDefault();
			if (listen.status !== 'idle') listen.skip(-1);
			else gotoChapter(chapter.prev);
		} else if (e.key === ' ') {
			e.preventDefault();
			window.scrollBy({
				top: (e.shiftKey ? -1 : 1) * window.innerHeight * 0.85,
				behavior: 'smooth'
			});
		}
	}

	/** Edge tap zones on touch devices: outer 15% turns the chapter. */
	function onArticleClick(e: MouseEvent) {
		if (!window.matchMedia('(pointer: coarse)').matches) return;
		const el = e.target as HTMLElement;
		if (el.closest('a, button, mark, input, textarea, select, .selbar, .define-pop')) return;
		if (window.getSelection()?.toString()) return;
		const x = e.clientX / window.innerWidth;
		if (x < 0.15) gotoChapter(chapter.prev);
		else if (x > 0.85) gotoChapter(chapter.next);
	}

	// Prefetch the next chapter when the browser is idle: the plain GET flows
	// through the service worker's stale-while-revalidate cache, so the next
	// tap is instant and the chapter becomes readable offline too.
	$effect(() => {
		const next = chapter.next;
		const s = slug;
		const language = getLang();
		if (!next) return;
		const url = `${API_BASE_URL}/api/library/books/${s}/chapters/${next.order}/?language=${language}`;
		// timeout guarantees the prefetch even when idle never comes (busy or
		// backgrounded tab); setTimeout covers browsers without rIC (Safari).
		const idle =
			'requestIdleCallback' in window
				? (fn: () => void) =>
						(window as Window & {
							requestIdleCallback: (cb: () => void, opts?: { timeout: number }) => number;
						}).requestIdleCallback(fn, { timeout: 3000 })
				: (fn: () => void) => setTimeout(fn, 1500);
		idle(() => {
			fetch(url).catch(() => {});
		});
	});

	// Reading-plan context (?plan=<slug>&day=<n>): show the Day N of M strip and
	// a mark-done action. The plan is fetched lazily — only when the params are
	// present — and cached across day navigations within the same plan.
	const planSlug = $derived($page.url.searchParams.get('plan'));
	const planDay = $derived(Number($page.url.searchParams.get('day')) || 0);
	let plan = $state<PlanDetail | null>(null);
	$effect(() => {
		const s = planSlug;
		if (!s) {
			plan = null;
			return;
		}
		if (plan?.slug === s) return;
		getPlan(s, getLang())
			.then((p) => (plan = p))
			.catch(() => (plan = null));
	});

	/** Mark today done, then continue: next day's chapter, or back to the plan. */
	function completePlanDay() {
		if (!plan || !planDay) return;
		planProgress.markDone(plan.slug, planDay);
		const next = planProgress.nextDay(plan.slug, plan.day_count);
		const nextEntry = next && plan.days.find((d) => d.day === next);
		if (nextEntry) {
			goto(`/books/${nextEntry.book_slug}/${nextEntry.chapter_order}?plan=${plan.slug}&day=${nextEntry.day}`);
		} else {
			goto(`/plans/${plan.slug}`);
		}
	}

	/** Read the chapter aloud from the topmost visible paragraph. */
	function startListening() {
		if (!body) return;
		const paragraphs = [...body.children].map((el) => (el as HTMLElement).innerText);
		listen.start(paragraphs, topVisibleIndex(), getLang());
	}

	function topVisibleIndex(): number {
		if (!body) return 0;
		const kids = body.children;
		for (let i = 0; i < kids.length; i++) {
			if (kids[i].getBoundingClientRect().bottom > HEADER_OFFSET) return i;
		}
		return 0;
	}

	// Highlight the paragraph being spoken and keep it in view.
	$effect(() => {
		const current = listen.current;
		if (!body) return;
		const kids = body.children;
		for (let i = 0; i < kids.length; i++) {
			kids[i].classList.toggle('tts-current', i === current);
		}
		if (current >= 0 && kids[current]) {
			kids[current].scrollIntoView({ block: 'center', behavior: 'smooth' });
		}
	});

	function restoreScroll(s: string, order: number) {
		// Prefer the device-local anchor; fall back to the synced resume point so
		// "continue reading" lands on the right paragraph on a fresh device too.
		const rec = getProgressRecord(s);
		const idx =
			getScrollAnchor(s, order) ??
			(rec && rec.order === order ? rec.paragraph_index : null);
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

	// Render text-range marks as <mark> spans; clicking one opens its note.
	$effect(() => {
		const list = marks.list;
		if (!body) return;
		renderMarks(body, list, (id) => {
			noteId = id;
			notePending = [];
			noteDraft = marks.getNote(id);
			noteOpen = true;
		});
	});

	const cite = $derived({
		author: chapter.author_name,
		book: chapter.book_title,
		chapter: chapter.title,
		url: $page.url.href
	});

	/** Note on a fresh selection: highlight it first, then attach the note. */
	function openNoteForSelection(segments: { p: number; s: number; e: number }[]) {
		const existing = marks.groupCovering(segments);
		noteId = existing;
		notePending = existing ? [] : segments;
		noteDraft = existing ? marks.getNote(existing) : '';
		noteOpen = true;
	}
	function saveNote() {
		if (noteId) {
			marks.setNote(noteId, noteDraft);
		} else if (notePending.length && noteDraft.trim()) {
			marks.add(notePending, noteDraft);
		}
		noteOpen = false;
	}
	function removeMark() {
		if (noteId) marks.remove(noteId);
		noteOpen = false;
	}
</script>

<svelte:head><title>{chapter.title} — {chapter.book_title} — Ochorus</title></svelte:head>
<svelte:window onscroll={onScroll} onkeydown={onKeydown} />

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
				<button
					class="btn btn-ghost !px-2.5 !py-1"
					onclick={() => (tocOpen = true)}
					aria-label={t('reader.contents')}
					title={t('reader.contents')}>☰</button
				>
				{#if listen.supported}
					<button
						class="btn btn-ghost !px-2.5 !py-1"
						class:!text-accent={listen.status !== 'idle'}
						onclick={() => (listen.status === 'idle' ? startListening() : listen.stop())}
						aria-label={t('reader.listen')}
						title={t('reader.listen')}>▶</button
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

<!-- svelte-ignore a11y_no_noninteractive_element_interactions, a11y_click_events_have_key_events -->
<article
	class="mx-auto px-5 py-10"
	style="{readerPrefs.style}; max-width: var(--reading-measure)"
	dir="auto"
	onclick={onArticleClick}
>
	<!-- Breadcrumb -->
	<nav class="mb-5 flex flex-wrap items-center gap-1.5 text-small text-muted" aria-label="Breadcrumb">
		<a href="/books" class="hover:text-text">{t('nav.books')}</a>
		<span>›</span>
		<a href="/authors/{chapter.author_slug}" class="hover:text-text">{chapter.author_name}</a>
		<span>›</span>
		<a href="/books/{slug}" class="hover:text-text">{chapter.book_title}</a>
	</nav>

	{#if plan && planDay}
		<div
			class="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-card border border-border bg-surface-2 px-4 py-3"
		>
			<div class="min-w-0">
				<a href="/plans/{plan.slug}" class="block truncate text-small font-semibold text-text hover:text-accent">
					{plan.title}
				</a>
				<span class="text-small text-muted">
					{t('plans.day')} {planDay} {t('plans.of')} {plan.day_count}
				</span>
			</div>
			{#if planProgress.isDone(plan.slug, planDay)}
				<span class="text-small font-semibold text-accent">✓ {t('plans.dayDone')}</span>
			{:else}
				<button class="btn btn-primary !py-1.5 text-small" onclick={completePlanDay}>
					{t('plans.markDone')}
				</button>
			{/if}
		</div>
	{/if}

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
	onHighlight={(segments) => {
		const existing = marks.groupCovering(segments);
		if (existing) marks.remove(existing);
		else marks.add(segments);
	}}
	onNote={openNoteForSelection}
	isHighlighted={(segments) => marks.groupCovering(segments) !== null}
	onDefine={(word, top, left) => define.show(word, top, left)}
/>

<DefinePopover />

<TocDrawer {slug} currentOrder={chapter.order} bind:open={tocOpen} />

<ListenBar />

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
			<div class="mt-3 flex items-center gap-2">
				{#if noteId}
					<button class="btn btn-ghost !text-red-700 dark:!text-red-400" onclick={removeMark}>
						{t('reader.removeHighlight')}
					</button>
				{/if}
				<span class="flex-1"></span>
				<button class="btn btn-ghost" onclick={() => (noteOpen = false)}>Cancel</button>
				<button class="btn btn-primary" onclick={saveNote}>Save</button>
			</div>
		</div>
	</div>
{/if}

<style>
	/* Text-range marks: <mark> spans wrapped around the selected text. */
	:global(.reading mark.range-mark) {
		background: color-mix(in srgb, var(--gold) 28%, transparent);
		color: inherit;
		border-radius: 2px;
		padding: 0.08em 0;
		box-decoration-break: clone;
		-webkit-box-decoration-break: clone;
		cursor: pointer;
	}
	:global(.reading mark.range-mark:hover) {
		background: color-mix(in srgb, var(--gold) 42%, transparent);
	}
	/* A mark carrying a note gets a subtle underline cue. */
	:global(.reading mark.range-mark.has-note) {
		border-bottom: 2px solid var(--gold);
	}
	/* Paragraph currently being read aloud in Listen mode. */
	:global(.reading > .tts-current) {
		background: color-mix(in srgb, var(--accent) 10%, transparent);
		border-radius: 4px;
		box-shadow: 0 0 0 6px color-mix(in srgb, var(--accent) 10%, transparent);
		transition: background 0.3s ease;
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
