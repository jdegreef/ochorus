<script lang="ts">
	/**
	 * The reading machinery every long-form work shares — the prose itself, and
	 * everything that has to know about it.
	 *
	 * Ochorus has three kinds of long prose — book chapters, sermons and author
	 * biographies — and each needs the same things: a resume point that survives a
	 * text-size change, highlights and notes, read-aloud with follow-along, the
	 * dictionary and scripture popovers, and search-hit rendering. That was built
	 * for chapters, copied to sermons, and the copy silently drifted (the sermon
	 * reader never gained bookmarks). This owns it once.
	 *
	 * It deliberately does NOT own the page: no <article>, no sticky top bar, no
	 * time-remaining pill. Those looked shared when only the sermon page existed,
	 * but the three surfaces genuinely differ — a biography's prose is one band in
	 * a wider page (portrait, timeline, book grid) that must not inherit
	 * `--reading-measure`, and the chapter reader's paged layout needs its own
	 * article element, its own bottom scrubber, and a bar that switches to
	 * `fixed`. A component whose extension point is "escape my container" should
	 * not own the container. So each route renders its own shell and reads what it
	 * needs from here: `bind:frac` for a progress bar, `bind:body` for an outline,
	 * `startListening()` for a Listen button.
	 *
	 * `kind` namespaces every stored key — that plumbing already understands
	 * 'book' | 'sermon' | 'bio' end to end (localStorage prefix, API, and the
	 * Django column), so a new surface needs no migration.
	 */
	import { onMount, tick } from 'svelte';
	import { page } from '$app/stores';
	import { i18n } from '$lib/i18n.svelte';
	import { HEADER_OFFSET } from '$lib/reading';
	import { getScrollAnchor, saveScrollAnchor, saveProgress, getProgressRecord } from '$lib/progress';
	import { HIGHLIGHT_COLORS, DEFAULT_HIGHLIGHT, type WorkKind } from '$lib/reading-schema';
	import { marks, type Segment } from '$lib/marks.svelte';
	import { renderMarks } from '$lib/rangeMarks';
	import { findQueryHits } from '$lib/searchHits';
	import { listen } from '$lib/listen.svelte';
	import { define } from '$lib/define.svelte';
	import { scripture } from '$lib/scripture.svelte';
	import { getLang } from '$lib/lang.svelte';
	import { focusTrap } from '$lib/actions/focusTrap';
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
		/** Attribution for copy/share from the selection bar. */
		cite: { author: string; book: string; chapter: string; url: string };
		/** Shown in the OS media session while reading aloud. */
		listenTitle: string;
		listenArtist: string;
		/** Extra classes on the prose element, for surfaces with their own band width. */
		class?: string;
		/** The rendered prose, for pages that measure it (outlines, bookmarks). */
		body?: HTMLElement;
		/**
		 * How far through the prose the reader is, 0–1. Bind it to drive a progress
		 * bar or a time-remaining estimate in whatever chrome the page renders.
		 */
		frac?: number;
		/**
		 * Height of the page's own sticky chrome, in px — how far down the viewport
		 * "the top" really is. Both halves of the resume cycle use it, so they must
		 * agree: restoring parks a paragraph just below it, and the next save asks
		 * which paragraph is first below it.
		 *
		 * Getting it wrong drifts the resume point BACKWARDS. A page with no sticky
		 * bar that inherits 64 leaves the previous paragraph's last line above the
		 * threshold, so the next scroll saves N-1, and every reopen walks back one
		 * more. Defaults to the readers' bar height; surfaces without one pass 0.
		 */
		headerOffset?: number;
	}

	let {
		kind,
		slug,
		order = 1,
		language,
		html,
		cite,
		listenTitle,
		listenArtist,
		class: className = '',
		body = $bindable(),
		frac = $bindable(0),
		headerOffset = HEADER_OFFSET
	}: Props = $props();

	const t = i18n.t;

	// --- Position --------------------------------------------------------------
	// Anchored to the top-visible paragraph, not a pixel offset, so a saved spot
	// survives a change of text size or column width.
	let saveTimer: ReturnType<typeof setTimeout> | undefined;

	/** Index of the first block still on screen. Pages need this for bookmarks. */
	export function topVisibleIndex(): number {
		if (!body) return 0;
		const kids = body.children;
		for (let i = 0; i < kids.length; i++) {
			if (kids[i].getBoundingClientRect().bottom > headerOffset) return i;
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
		const key = `${kind}:${slug}:${order}`;
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
				window.scrollBy(0, -headerOffset);
			}
			updateFraction();
		})();
	});

	// Marks can be replaced underneath us (sign-in merge / sign-out wipe), and a
	// scroll-save timer must not outlive the page.
	onMount(() => {
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
	export function startListening() {
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
					// Both axes: the chapter reader lays pages out in columns and scrolls
					// horizontally, so `block` alone would never reach a hit on a later
					// page.
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

<!-- Body HTML is cleaned server-side to a safe tag subset on ingest; Bible
     references are wrapped as tappable spans (scripture popover). -->
<!-- svelte-ignore a11y_no_noninteractive_element_interactions, a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
<!-- eslint-disable-next-line svelte/no-at-html-tags -->
<div class="reading {className}" bind:this={body} onclick={onBodyClick} dir="auto">{@html html}</div>

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
				class="w-full rounded-sm border border-border-strong bg-bg p-3 text-body text-text"
				aria-label={t('reader.note')}
				placeholder="…"
			></textarea>
			<div class="mt-3 flex items-center gap-2">
				{#if noteId}
					<button class="btn btn-ghost !text-danger" onclick={removeMark}>
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
