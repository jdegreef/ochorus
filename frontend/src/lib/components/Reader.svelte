<script lang="ts">
	/**
	 * The reading surface every long-form work shares.
	 *
	 * Ochorus has three kinds of long prose — book chapters, sermons and author
	 * biographies — and each one needs the same things: the reader's typography
	 * preferences, a resume point, highlights and notes, read-aloud, the
	 * dictionary and scripture popovers, and a way to hide the chrome. Those were
	 * built for chapters, copied to sermons, and the copy silently drifted (the
	 * sermon reader never gained bookmarks). This component owns that machinery
	 * once so a third surface adopts it instead of forking it again.
	 *
	 * It owns the *reading* — progress, position, marks, speech, popovers, and the
	 * <article> shell that carries the reader's CSS variables. It deliberately
	 * owns none of the *work* — titles, bylines, epigraphs, footers, structured
	 * data and per-kind navigation are the page's business, passed in through the
	 * `header` / `footer` / `actions` snippets.
	 *
	 * Position is stored as a paragraph index, not a pixel offset, so a saved spot
	 * survives a change of text size or column width (see `progress.ts`). The
	 * `kind` prop namespaces every stored key — that plumbing already understands
	 * 'book' | 'sermon' | 'bio' (see `reading-schema.ts`).
	 */
	import { onMount, tick, type Snippet } from 'svelte';
	import { page } from '$app/stores';
	import { readerPrefs } from '$lib/readerPrefs.svelte';
	import { readerUi } from '$lib/readerUi.svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { readingMinutes, HEADER_OFFSET } from '$lib/reading';
	import {
		getScrollAnchor,
		saveScrollAnchor,
		saveProgress,
		getProgressRecord
	} from '$lib/progress';
	import { HIGHLIGHT_COLORS, DEFAULT_HIGHLIGHT, type WorkKind } from '$lib/reading-schema';
	import { marks, type Segment } from '$lib/marks.svelte';
	import { renderMarks } from '$lib/rangeMarks';
	import { findQueryHits } from '$lib/searchHits';
	import { listen } from '$lib/listen.svelte';
	import { define } from '$lib/define.svelte';
	import { scripture } from '$lib/scripture.svelte';
	import { getLang } from '$lib/lang.svelte';
	import { focusTrap } from '$lib/actions/focusTrap';
	import ReaderControls from '$lib/components/ReaderControls.svelte';
	import ScripturePopover from '$lib/components/ScripturePopover.svelte';
	import DefinePopover from '$lib/components/DefinePopover.svelte';
	import SelectionBar from '$lib/components/SelectionBar.svelte';
	import ListenBar from '$lib/components/ListenBar.svelte';

	interface Props {
		/** Namespaces every stored key (position, anchors, marks). */
		kind: WorkKind;
		/** Identifies the work within its kind. For a bio, the author's slug. */
		slug: string;
		/** Chapters pass their order; single-document kinds (sermon, bio) get 1. */
		order?: number;
		language: string;
		/** Server-cleaned body HTML. Scripture refs arrive pre-wrapped. */
		html: string;
		/** Drives the time-remaining estimate. */
		wordCount: number;
		/** Attribution for copy/share from the selection bar. */
		cite: { author: string; book: string; chapter: string; url: string };
		/** Shown in the OS media session while reading aloud. */
		listenTitle: string;
		listenArtist: string;
		/**
		 * Suffix for the time-remaining pill ("… min left").
		 *
		 * A prop only because the copy differs per surface and the bio's wording
		 * isn't settled yet. It is the one translated string this component takes
		 * rather than resolving itself, which also hides the key from the
		 * i18n-parity check — fold it back into a `reader.minLeft_<kind>` lookup
		 * once the third caller lands and the wording is known.
		 */
		minLeftLabel: string;
		/** Top-bar link back to the containing collection. */
		backHref: string;
		backLabel: string;
		/** The rendered body, so a page can derive an outline from it. */
		body?: HTMLElement;
		/** Fires on scroll, for page-owned scroll effects (the sermon outline). */
		onScroll?: () => void;
		/** Extra top-bar buttons, rendered before the built-in ones. */
		actions?: Snippet;
		/** Page content inside the <article>, above and below the prose. */
		header?: Snippet;
		footer?: Snippet;
		/** Anything that must sit outside the <article> (panels, rails). */
		overlays?: Snippet;
	}

	let {
		kind,
		slug,
		order = 1,
		language,
		html,
		wordCount,
		cite,
		listenTitle,
		listenArtist,
		minLeftLabel,
		backHref,
		backLabel,
		body = $bindable(),
		onScroll,
		actions,
		header,
		footer,
		overlays
	}: Props = $props();

	const t = i18n.t;

	// --- Reading progress ------------------------------------------------------
	// Long prose needs orientation: a scroll-progress bar, an estimate of the time
	// remaining, and a resume point. Anchored to the top-visible paragraph so it
	// survives text-size / width changes.
	let frac = $state(0);
	let saveTimer: ReturnType<typeof setTimeout> | undefined;
	const minutesLeft = $derived(Math.max(1, Math.ceil(readingMinutes(wordCount) * (1 - frac))));

	function topVisibleIndex(): number {
		if (!body) return 0;
		const kids = body.children;
		for (let i = 0; i < kids.length; i++) {
			if (kids[i].getBoundingClientRect().bottom > HEADER_OFFSET) return i;
		}
		return Math.max(0, kids.length - 1);
	}

	function updateFraction() {
		if (!body) return;
		const rect = body.getBoundingClientRect();
		if (rect.height <= 0) return;
		const seen = Math.min(Math.max(window.innerHeight - rect.top, 0), rect.height);
		frac = Math.min(1, Math.max(0, seen / rect.height));
	}

	function handleScroll() {
		onScroll?.();
		clearTimeout(saveTimer);
		saveTimer = setTimeout(() => {
			updateFraction();
			saveScrollAnchor(slug, order, topVisibleIndex(), kind);
		}, 250);
	}

	// Record the visit (so the work lands in "Continue reading") and restore the
	// saved spot — a `?p=` deep link (notebook highlights) wins over the device
	// anchor. Effect, not onMount: client-side nav between works reuses this
	// component.
	let restoredFor = '';
	$effect(() => {
		const key = `${kind}:${slug}`;
		if (!body || restoredFor === key) return;
		restoredFor = key;
		// A pending scroll-save from the PREVIOUS work must not fire against this
		// one's body (it would record a bogus synced resume point).
		clearTimeout(saveTimer);
		// Seed a ?p= deep link into the anchor FIRST so the progress record (and
		// the resume point that syncs to the account) starts at the jumped-to
		// paragraph.
		const fromUrl = Number($page.url.searchParams.get('p'));
		if (Number.isFinite(fromUrl) && fromUrl > 0) {
			saveScrollAnchor(slug, order, fromUrl, kind);
		}
		saveProgress(slug, order, language, kind);
		(async () => {
			await tick();
			// Deep link > device anchor > synced resume point (fresh device).
			const idx =
				Number.isFinite(fromUrl) && fromUrl > 0
					? fromUrl
					: (getScrollAnchor(slug, order, kind) ??
						getProgressRecord(slug, kind)?.paragraph_index ??
						0);
			if (idx > 0 && body?.children[idx]) {
				body.children[idx].scrollIntoView({ block: 'start' });
				window.scrollBy(0, -HEADER_OFFSET);
			}
			updateFraction();
		})();
	});

	// Marks can be replaced underneath us (sign-in merge / sign-out wipe), and a
	// scroll-save timer must not outlive the page.
	onMount(() => {
		readerPrefs.init();
		listen.init();
		const onSync = () => marks.refresh();
		window.addEventListener('ochorus:sync', onSync);
		return () => {
			clearTimeout(saveTimer);
			window.removeEventListener('ochorus:sync', onSync);
		};
	});

	/** Tap a server-wrapped Bible reference → open the scripture popover. */
	function onBodyClick(e: MouseEvent) {
		const a = (e.target as HTMLElement).closest?.('a.scripture-ref') as HTMLElement | null;
		if (!a?.dataset.ref) return;
		e.preventDefault();
		const r = a.getBoundingClientRect();
		scripture.show(a.dataset.ref, r.bottom + window.scrollY, r.left + window.scrollX + r.width / 2);
	}

	/** Read aloud, starting from the paragraph you're reading. */
	function startListening() {
		if (!body) return;
		const paragraphs = [...body.children].map((el) => (el as HTMLElement).innerText);
		listen.start(paragraphs, topVisibleIndex(), getLang(), {
			title: listenTitle,
			artist: listenArtist
		});
	}

	// Follow-along: highlight the paragraph being spoken and keep it in view.
	// Track the marked element rather than toggling the class over every block —
	// a long chapter is 76+ blocks and this fires on every paragraph.
	let spokenEl: Element | null = null;
	$effect(() => {
		const current = listen.current;
		if (!body) return;
		spokenEl?.classList.remove('tts-current');
		spokenEl = body.children[current] ?? null;
		if (spokenEl) {
			spokenEl.classList.add('tts-current');
			spokenEl.scrollIntoView({ block: 'center', behavior: 'smooth' });
		}
	});

	// Stop speech when navigating to another work or leaving the page.
	$effect(() => {
		void slug;
		return () => listen.stop();
	});

	// --- Highlights & notes ----------------------------------------------------
	// Device-local text-range marks over the body. A note editor opens on tap of a
	// marked span or via the selection bar's "Note".
	let noteOpen = $state(false);
	let noteId = $state<string | null>(null);
	let notePending = $state<Segment[]>([]);
	let noteDraft = $state('');
	let noteColor = $state<string>(DEFAULT_HIGHLIGHT);

	$effect(() => {
		// Reload when navigating between works.
		marks.load(slug, order, language, kind);
	});

	// Paint marks as <mark> spans; clicking one opens its note editor. Arriving
	// from a search result: highlight what matched and scroll to it, rather than
	// dropping the reader at the top to re-find their sentence. Offsets are
	// computed from the rendered blocks and handed to the SAME renderer the
	// highlights use — that function restores each block from `dataset.pristine`,
	// so a separate pass would be wiped whenever a highlight changed, and the two
	// would fight over the same HTML.
	const searchQuery = $derived(($page.url.searchParams.get('q') ?? '').trim());
	let scrolledToHit = false;

	$effect(() => {
		const list = marks.list;
		if (!body) return;
		// Recomputed here, not once on mount: the marks render restores pristine
		// HTML, so hit offsets have to be handed over on every pass.
		const hits = searchQuery
			? findQueryHits(
					Array.from(body.children).map((el) => el.textContent ?? ''),
					searchQuery
				)
			: [];
		renderMarks(
			body,
			list,
			(id) => {
				noteId = id;
				notePending = [];
				noteDraft = marks.getNote(id);
				noteColor = marks.getColor(id);
				noteOpen = true;
			},
			hits
		);

		// Once per arrival: bring the first match into view. Guarded, or every
		// highlight edit would yank the reader back up the page.
		if (hits.length && !scrolledToHit) {
			scrolledToHit = true;
			requestAnimationFrame(() =>
				body
					?.querySelector('mark.search-hit')
					// Both axes: the paged reader lays chapters out in columns and
					// scrolls horizontally, so `block` alone would never reach a hit on
					// a later page.
					?.scrollIntoView({ block: 'center', inline: 'center', behavior: 'smooth' })
			);
		}
	});

	/** Note on a fresh selection: highlight it first, then attach the note. */
	function openNoteForSelection(segments: Segment[]) {
		const existing = marks.groupCovering(segments);
		noteId = existing;
		notePending = existing ? [] : segments;
		noteDraft = existing ? marks.getNote(existing) : '';
		noteColor = existing ? marks.getColor(existing) : DEFAULT_HIGHLIGHT;
		noteOpen = true;
	}
	function saveNote() {
		if (noteId) {
			marks.setNote(noteId, noteDraft);
			marks.setColor(noteId, noteColor);
		} else if (notePending.length && noteDraft.trim()) {
			marks.add(notePending, noteDraft, noteColor);
		}
		noteOpen = false;
	}
	function removeMark() {
		if (noteId) marks.remove(noteId);
		noteOpen = false;
	}
</script>

<svelte:window onscroll={handleScroll} />

<!-- Scroll-progress bar, pinned to the very top of the viewport. -->
<div class="read-progress" style="transform: scaleX({frac})" aria-hidden="true"></div>

<!-- Reader top bar -->
{#if !readerUi.focus}
	<div class="sticky top-0 z-10 border-b border-border bg-bg/90 backdrop-blur">
		<div class="mx-auto flex max-w-3xl items-center justify-between gap-3 px-5 py-2.5">
			<a href={backHref} class="text-small text-muted hover:text-text">← {backLabel}</a>
			<div class="flex shrink-0 items-center gap-1">
				{@render actions?.()}
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
		class="fixed end-4 top-4 z-30 rounded-full border border-border bg-surface/90 px-3 py-1.5 text-small text-muted shadow-md backdrop-blur hover:text-text"
		onclick={() => readerUi.exitFocus()}>✕ {t('reader.exitFocus')}</button
	>
{/if}

{@render overlays?.()}

<article class="mx-auto px-5 py-10" style="{readerPrefs.style}; max-width: var(--reading-measure)">
	{@render header?.()}

	<!-- Body HTML is cleaned server-side to a safe tag subset on ingest; Bible
	     references are wrapped as tappable spans (scripture popover). -->
	<!-- svelte-ignore a11y_no_noninteractive_element_interactions, a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
	<div class="reading" bind:this={body} onclick={onBodyClick} dir="auto">{@html html}</div>

	{@render footer?.()}
</article>

<!-- Time-remaining pill; hidden in focus and while listening. -->
{#if !readerUi.focus && listen.status === 'idle' && frac < 0.99}
	<div class="min-left" aria-hidden="true">{minutesLeft} {minLeftLabel}</div>
{/if}

<SelectionBar
	container={body}
	{cite}
	onHighlight={(segments, color) => {
		const existing = marks.groupCovering(segments);
		if (!existing) marks.add(segments, undefined, color);
		else if (marks.getColor(existing) === color) marks.remove(existing);
		else marks.setColor(existing, color);
	}}
	onNote={openNoteForSelection}
	highlightColor={(segments) => {
		const id = marks.groupCovering(segments);
		return id ? marks.getColor(id) : null;
	}}
	onDefine={(word, top, left) => define.show(word, top, left)}
/>

<ScripturePopover />
<DefinePopover />
<ListenBar />

{#if noteOpen}
	<div
		class="note-overlay"
		role="dialog"
		aria-modal="true"
		aria-label={t('reader.note')}
		use:focusTrap={{ onEscape: () => (noteOpen = false) }}
	>
		<div class="note-card">
			<h2 class="mb-2 text-h3">{t('reader.note')}</h2>
			<div class="mb-3 flex items-center gap-2.5" role="group" aria-label={t('reader.highlight')}>
				{#each HIGHLIGHT_COLORS as color (color)}
					<button
						type="button"
						class="hl-swatch"
						data-color={color}
						class:active={noteColor === color}
						aria-pressed={noteColor === color}
						aria-label="{t('reader.highlight')}: {t(`reader.hl_${color}`)}"
						title={t(`reader.hl_${color}`)}
						onclick={() => (noteColor = color)}
					></button>
				{/each}
			</div>
			<textarea
				bind:value={noteDraft}
				rows="5"
				class="w-full rounded-sm border border-border bg-bg p-3 text-body text-text"
				aria-label={t('reader.note')}
				placeholder="…"
			></textarea>
			<div class="mt-3 flex items-center gap-2">
				{#if noteId}
					<button class="btn btn-ghost !text-red-700 dark:!text-red-400" onclick={removeMark}>
						{t('reader.removeHighlight')}
					</button>
				{/if}
				<span class="flex-1"></span>
				<button class="btn btn-ghost" onclick={() => (noteOpen = false)}>{t('common.cancel')}</button>
				<button class="btn btn-primary" onclick={saveNote}>{t('common.save')}</button>
			</div>
		</div>
	</div>
{/if}

<style>
	/* Scroll-progress bar: a thin accent line scaled by reading fraction. */
	.read-progress {
		position: fixed;
		top: 0;
		left: 0;
		right: 0;
		height: 2px;
		z-index: 40;
		background: var(--accent);
		transform-origin: left center;
		transition: transform 0.1s linear;
		pointer-events: none;
	}
	.min-left {
		position: fixed;
		bottom: 1rem;
		left: 50%;
		transform: translateX(-50%);
		z-index: 30;
		border-radius: 9999px;
		border: 1px solid var(--border);
		background: color-mix(in srgb, var(--bg) 85%, transparent);
		backdrop-filter: blur(6px);
		padding: 0.25rem 0.8rem;
		font-size: 0.72rem;
		color: var(--muted);
		pointer-events: none;
	}

	/* Paragraph currently being read aloud in Listen mode. */
	:global(.reading > .tts-current) {
		background: color-mix(in srgb, var(--accent) 10%, transparent);
		border-radius: 4px;
		box-shadow: 0 0 0 6px color-mix(in srgb, var(--accent) 10%, transparent);
		transition: background 0.3s ease;
	}

	/* Text-range marks (<mark> spans) are styled globally in app.css. */
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
