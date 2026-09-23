<script lang="ts">
	import { tick } from 'svelte';
	import { i18n } from '$lib/i18n.svelte';
	import { segmentsFromSelection } from '$lib/rangeMarks';
	import { readerProse } from '$lib/listenText';
	import { HIGHLIGHT_COLORS } from '$lib/reading-schema';
	import { shareQuoteCard } from '$lib/quoteCard';
	import { clampPopoverLeft, HEADER_OFFSET } from '$lib/reading';
	import type { Segment } from '$lib/marks.svelte';

	/**
	 * The bar's size before it has ever been drawn — its max-width and two rows.
	 * Only the first placement uses these: the bar is then measured as drawn
	 * (`place`), so a language with longer labels, a row that wraps on a phone,
	 * or a button added later needs no retuning here.
	 */
	const FIRST_WIDTH = 448;
	const FIRST_HEIGHT = 84;
	/** Keep this much clear of either viewport edge. */
	const GUTTER = 12;

	interface Cite {
		author: string;
		book: string;
		chapter: string;
		url: string;
	}

	let {
		container,
		cite,
		language,
		onHighlight,
		onNote,
		highlightColor,
		onDefine,
		onDefineClose,
		onJournal,
		onSuggestEdit
	}: {
		container: HTMLElement | undefined;
		cite: Cite;
		/** The edition's language, so a quote card is set in its own script. */
		language: string;
		/** Toggle/recolour: called with the picked colour key. */
		onHighlight?: (segments: Segment[], color: string) => void;
		onNote?: (segments: Segment[]) => void;
		/** Current highlight colour of the selection, or null if not highlighted. */
		highlightColor?: (segments: Segment[]) => string | null;
		onDefine?: (word: string, top: number, left: number) => void;
		/** Retire a definition opened for a word the selection has since outgrown. */
		onDefineClose?: () => void;
		/** Start a Notebook note or prayer about the selected passage. */
		onJournal?: (kind: 'note' | 'prayer', quote: string, segments: Segment[]) => void;
		/** Send feedback / suggest an edit on the selected passage. */
		onSuggestEdit?: (quote: string, segments: Segment[]) => void;
	} = $props();
	const t = i18n.t;

	let visible = $state(false);
	let bar = $state<HTMLElement>();
	let top = $state(0);
	let left = $state(0);
	/** Bar sits below the selection when there is no room above it. */
	let below = $state(false);
	let selectedText = $state('');
	let segments = $state<Segment[]>([]);
	let copied = $state(false);
	let cardBusy = $state(false);

	/**
	 * A pointer-driven selection in progress. Its intermediate states are not
	 * what the reader means yet, so the define branch waits for the gesture.
	 */
	let dragging = false;
	let defineTimer: ReturnType<typeof setTimeout>;

	/**
	 * How long a selection with no pointer gesture behind it must hold before a
	 * definition is looked up. Keyboard selection (shift+arrow) has no pointerup
	 * to settle on and would otherwise fire on every two-character state it
	 * passes through.
	 */
	const DEFINE_SETTLE_MS = 250;

	function attribution(): string {
		const where = cite.chapter ? `${cite.book}, ${cite.chapter}` : cite.book;
		return `“${selectedText}”\n— ${cite.author}, ${where}\n${cite.url}`;
	}

	/**
	 * `immediate` marks a gesture that has definitively ENDED (a pointerup), so
	 * a double-click or long-press still opens its definition at once. Every
	 * other caller debounces, which is what covers keyboard selection.
	 */
	function update(immediate = false) {
		clearTimeout(defineTimer);
		const sel = window.getSelection();
		const text = sel?.toString().trim() ?? '';
		const inContainer =
			!!sel &&
			sel.rangeCount > 0 &&
			!!container &&
			container.contains(sel.anchorNode) &&
			container.contains(sel.focusNode);

		// A single selected word (double-click / mobile long-press) opens the
		// definition popover instead of the action bar — but only where a
		// definition can actually exist. The glossary and the dictionary behind
		// it are English, so this stays Latin-script on purpose; \p{Script=Latin}
		// rather than [A-Za-z] so accented Spanish and Swahili words qualify.
		//
		// Anything else — an Arabic word, say — deliberately FALLS THROUGH to the
		// action bar below, which is the part that must work in every language.
		// Routing it here instead would strip it to nothing and show neither.
		if (inContainer && onDefine && /^[\p{Script=Latin}\p{M}’'-]{2,}$/u.test(text)) {
			visible = false;
			// DEFERRED, never immediate. `selectionchange` fires on every
			// intermediate state of a drag, so starting a drag mid-word — inside
			// "**Go**spel" — used to open the dictionary on "Go" and send a lookup
			// for it, mid-gesture, on nearly every selection that begins mid-word.
			// The popover then sat there next to the action bar until the next
			// mousedown, for a word the reader never chose.
			if (dragging) return;
			const rect = sel.getRangeAt(0).getBoundingClientRect();
			const word = text;
			const top = rect.bottom + window.scrollY;
			const left = rect.left + window.scrollX + rect.width / 2;
			if (immediate) onDefine(word, top, left);
			else defineTimer = setTimeout(() => onDefine(word, top, left), DEFINE_SETTLE_MS);
			return;
		}

		// Past one word now, so retire a definition opened for a word this
		// selection has grown beyond — `update()` used to fall straight through
		// to the action bar and leave it open alongside.
		//
		// Guarded on there BEING a selection: an empty one is a click, possibly
		// into the popover itself, and must not dismiss it.
		if (inContainer && text.length >= 2) onDefineClose?.();

		// Two characters, not four: the old floor silently refused to highlight or
		// share a short quote, and "God", "Amen" and most Arabic words are under
		// it.
		if (!inContainer || text.length < 2) {
			visible = false;
			return;
		}
		selectedText = text;
		segments = segmentsFromSelection(container, sel);
		const rect = sel.getRangeAt(0).getBoundingClientRect();

		place(rect);
		copied = false;
		visible = true;
		// Now that it is drawn with this selection's buttons, place it by its real size.
		tick().then(() => place(rect));
	}

	/**
	 * Selecting the first line of a chapter used to put the bar above the top of
	 * the page (and behind the sticky chrome). Flip it under the selection when
	 * there isn't room, and keep it inside the viewport horizontally — a
	 * selection near either margin ran half off-screen.
	 */
	function place(rect: DOMRect) {
		const width = bar?.offsetWidth || FIRST_WIDTH;
		const height = bar?.offsetHeight || FIRST_HEIGHT;
		below = rect.top < HEADER_OFFSET + height + 8;
		top = below ? rect.bottom + window.scrollY + 8 : rect.top + window.scrollY - 8;
		left = clampPopoverLeft(rect.left + rect.width / 2 + window.scrollX, width, GUTTER);
	}

	async function copy() {
		try {
			await navigator.clipboard.writeText(attribution());
			copied = true;
		} catch {
			copied = false;
		}
	}

	async function share() {
		const data = { title: cite.book, text: `“${selectedText}” — ${cite.author}`, url: cite.url };
		if (navigator.share) {
			try {
				await navigator.share(data);
			} catch {
				/* user dismissed */
			}
		} else {
			await copy();
		}
	}

	async function quoteCard() {
		if (cardBusy) return;
		// The quote card is the one artifact built to leave the site, so strip the
		// footnote markers (a `<sup>4</sup>`, an inline `[4]`) the selection carries
		// for the eye. Computed here from the live selection, not captured on every
		// `selectionchange`: it is only ever needed on this tap, and the bar's
		// mousedown-preventDefault keeps the range alive for the click (the same
		// reason `onHighlight` can still read the selection below).
		const sel = window.getSelection();
		if (!sel || sel.rangeCount === 0) return;
		const quote = readerProse(sel.getRangeAt(0).cloneContents());
		if (!quote) return; // a selection of nothing but a marker — no card to make
		cardBusy = true;
		try {
			await shareQuoteCard({
				quote,
				author: cite.author,
				source: cite.chapter ? `${cite.book}, ${cite.chapter}` : cite.book,
				site: 'ochorus.com',
				language
			});
		} catch {
			/* rendering/sharing failed — nothing to surface, the quote is still selected */
		} finally {
			cardBusy = false;
		}
	}

	/** The pointer gesture is over: re-evaluate, which is what actually opens a
	 *  definition for a deliberate double-click or long-press. */
	function settle() {
		if (!dragging) return;
		dragging = false;
		update(true);
	}

	/** Hand the passage to the Notebook — its text cleaned of footnote
	 *  markers, as the quote card does, since it will be quoted back. */
	function journal(kind: 'note' | 'prayer') {
		const sel = window.getSelection();
		const quote = sel && sel.rangeCount ? readerProse(sel.getRangeAt(0).cloneContents()) : selectedText;
		onJournal?.(kind, quote || selectedText, segments);
		sel?.removeAllRanges();
		visible = false;
	}

	/** Send feedback on the selected passage — same quote-cleaning as above. */
	function suggestEdit() {
		const sel = window.getSelection();
		const quote = sel && sel.rangeCount ? readerProse(sel.getRangeAt(0).cloneContents()) : selectedText;
		onSuggestEdit?.(quote || selectedText, segments);
		sel?.removeAllRanges();
		visible = false;
	}

	const activeColor = $derived(
		highlightColor && segments.length > 0 ? highlightColor(segments) : null
	);
</script>

<svelte:document
	onselectionchange={() => update()}
	onpointerdown={() => (dragging = true)}
	onpointerup={settle}
	onpointercancel={settle}
/>

{#if visible}
	<!--
	  Pressing a button must not collapse the selection. Without this, mousedown
	  clears the range, the queued `selectionchange` runs `update()`, `visible`
	  goes false, and the button unmounts BEFORE `click` fires — so Copy, Share
	  and the swatches silently did nothing, intermittently, per browser timing.
	  Suppressing the default mousedown behaviour keeps the selection (and the
	  bar) alive long enough for the click to land. Keyboard focus is unaffected:
	  Tab doesn't go through mousedown.
	-->
	<div
		bind:this={bar}
		class="selbar"
		class:below
		style="top: {top}px; left: {left}px"
		role="toolbar"
		aria-label={t('a11y.selectionActions')}
		tabindex="-1"
		onmousedown={(e) => e.preventDefault()}
	>
		<span class="selbar-main">
			<button class="selbar-btn" onclick={copy}>
				{copied ? '✓ ' : ''}{t('reader.copyQuote')}
			</button>
			<span class="selbar-sep"></span>
			<button class="selbar-btn" onclick={share}>{t('reader.share')}</button>
			<span class="selbar-sep"></span>
			<button class="selbar-btn" onclick={quoteCard} disabled={cardBusy}>
				{t('reader.quoteCard')}
			</button>
			{#if onHighlight && segments.length > 0}
				<span class="selbar-sep"></span>
				<span class="selbar-swatches" role="group" aria-label={t('reader.highlight')}>
					{#each HIGHLIGHT_COLORS as color (color)}
						<button
							class="hl-swatch"
							data-color={color}
							class:active={activeColor === color}
							aria-pressed={activeColor === color}
							aria-label="{t('reader.highlight')}: {t(`reader.hl_${color}`)}"
							title={t(`reader.hl_${color}`)}
							onclick={() => {
								onHighlight(segments, color);
								window.getSelection()?.removeAllRanges();
								visible = false;
							}}
						></button>
					{/each}
				</span>
			{/if}
			{#if onNote && segments.length > 0}
				<span class="selbar-sep"></span>
				<button
					class="selbar-btn"
					onclick={() => {
						onNote(segments);
						window.getSelection()?.removeAllRanges();
						visible = false;
					}}>{t('reader.note')}</button
				>
			{/if}
		</span>
		{#if onJournal && segments.length > 0}
			<!-- A second row: taking the passage into the Notebook. -->
			<span class="selbar-row">
				<button class="selbar-btn" onclick={() => journal('note')}>✎ {t('reader.writeAbout')}</button>
				<span class="selbar-sep"></span>
				<button class="selbar-btn" onclick={() => journal('prayer')}>🙏 {t('reader.prayThis')}</button>
			</span>
		{/if}
		{#if onSuggestEdit && segments.length > 0}
			<!-- Feedback on the passage — a suggested edit, into the admin queue. -->
			<span class="selbar-row">
				<button class="selbar-btn" onclick={suggestEdit}>{t('reader.suggestEdit')}</button>
			</span>
		{/if}
	</div>
{/if}

<style>
	.selbar {
		position: absolute;
		z-index: 40;
		display: flex;
		align-items: center;
		gap: 0.25rem;
		transform: translate(-50%, -100%);
		max-width: min(28rem, calc(100vw - 1.5rem));
		padding: 0.25rem;
		border-radius: var(--radius-sm);
		background: var(--surface);
		border: 1px solid var(--border);
		box-shadow: var(--shadow-popover);
		white-space: nowrap;
		flex-direction: column;
		align-items: stretch;
		/* Sized by its rows, not by the room between `left` and the container's
		   edge — an absolutely placed box shrinks to that, and the two-row bar
		   would otherwise squeeze its first row out past its own border. */
		width: max-content;
	}
	.selbar-main,
	.selbar-row {
		display: flex;
		align-items: center;
		gap: 0.25rem;
	}
	/* On a phone narrower than the row, wrap it rather than run past the edge. */
	.selbar-main {
		flex-wrap: wrap;
	}
	.selbar-row {
		padding-top: 0.25rem;
		border-top: 1px solid var(--border);
	}
	/* Flipped under the selection — see `below` in update(). */
	.selbar.below {
		transform: translate(-50%, 0);
	}
	.selbar-btn {
		padding: 0.35rem 0.6rem;
		border-radius: 6px;
		font-size: var(--fs-small);
		font-weight: 600;
		color: var(--text);
		cursor: pointer;
	}
	.selbar-btn:hover {
		background: var(--surface-2);
	}
	.selbar-swatches {
		display: flex;
		align-items: center;
		gap: 0.3rem;
		padding: 0 0.35rem;
	}
	.selbar-sep {
		width: 1px;
		align-self: stretch;
		background: var(--border);
	}
	/* .selbar-btn's 44px touch target lives in the global app.css
	   `@media (pointer: coarse)` block (a global selector matches this scoped
	   class by name), beside the other reader controls. */
</style>
