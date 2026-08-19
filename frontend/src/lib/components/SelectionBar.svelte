<script lang="ts">
	import { i18n } from '$lib/i18n.svelte';
	import { segmentsFromSelection } from '$lib/rangeMarks';
	import { HIGHLIGHT_COLORS } from '$lib/reading-schema';
	import { shareQuoteCard } from '$lib/quoteCard';
	import { HEADER_OFFSET } from '$lib/reading';
	import type { Segment } from '$lib/marks.svelte';

	/** Widest the bar gets (matches its max-width), for the viewport clamp. */
	const BAR_MAX_WIDTH = 352;
	/** Room the bar needs above a selection before it has to flip below it. */
	const BAR_CLEARANCE = 52;
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
		onHighlight,
		onNote,
		highlightColor,
		onDefine
	}: {
		container: HTMLElement | undefined;
		cite: Cite;
		/** Toggle/recolour: called with the picked colour key. */
		onHighlight?: (segments: Segment[], color: string) => void;
		onNote?: (segments: Segment[]) => void;
		/** Current highlight colour of the selection, or null if not highlighted. */
		highlightColor?: (segments: Segment[]) => string | null;
		onDefine?: (word: string, top: number, left: number) => void;
	} = $props();
	const t = i18n.t;

	let visible = $state(false);
	let top = $state(0);
	let left = $state(0);
	/** Bar sits below the selection when there is no room above it. */
	let below = $state(false);
	let selectedText = $state('');
	let segments = $state<Segment[]>([]);
	let copied = $state(false);
	let cardBusy = $state(false);

	function attribution(): string {
		const where = cite.chapter ? `${cite.book}, ${cite.chapter}` : cite.book;
		return `“${selectedText}”\n— ${cite.author}, ${where}\n${cite.url}`;
	}

	function update() {
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
			const rect = sel.getRangeAt(0).getBoundingClientRect();
			onDefine(text, rect.bottom + window.scrollY, rect.left + window.scrollX + rect.width / 2);
			visible = false;
			return;
		}

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

		// Selecting the first line of a chapter used to put the bar above the top
		// of the page (and behind the sticky chrome). Flip it under the selection
		// when there isn't room, and keep it inside the viewport horizontally —
		// a selection near either margin ran half off-screen.
		below = rect.top < HEADER_OFFSET + BAR_CLEARANCE;
		top = below ? rect.bottom + window.scrollY + 8 : rect.top + window.scrollY - 8;
		const half = BAR_MAX_WIDTH / 2;
		const centre = rect.left + rect.width / 2;
		left =
			Math.min(Math.max(centre, half + GUTTER), window.innerWidth - half - GUTTER) +
			window.scrollX;
		copied = false;
		visible = true;
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
		cardBusy = true;
		try {
			await shareQuoteCard({
				quote: selectedText,
				author: cite.author,
				source: cite.chapter ? `${cite.book}, ${cite.chapter}` : cite.book,
				site: 'ochorus.com'
			});
		} catch {
			/* rendering/sharing failed — nothing to surface, the quote is still selected */
		} finally {
			cardBusy = false;
		}
	}

	const activeColor = $derived(
		highlightColor && segments.length > 0 ? highlightColor(segments) : null
	);
</script>

<svelte:document onselectionchange={update} />

{#if visible}
	<div
		class="selbar"
		class:below
		style="top: {top}px; left: {left}px"
		role="toolbar"
		aria-label={t('a11y.selectionActions')}
	>
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
		max-width: min(22rem, calc(100vw - 1.5rem));
		padding: 0.25rem;
		border-radius: var(--radius-sm);
		background: var(--surface);
		border: 1px solid var(--border);
		box-shadow: var(--shadow-popover);
		white-space: nowrap;
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
</style>
