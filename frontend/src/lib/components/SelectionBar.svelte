<script lang="ts">
	import { i18n } from '$lib/i18n.svelte';
	import { segmentsFromSelection } from '$lib/rangeMarks';
	import { HIGHLIGHT_COLORS } from '$lib/reading-schema';
	import { shareQuoteCard } from '$lib/quoteCard';
	import type { Segment } from '$lib/marks.svelte';

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
		// definition popover instead of the action bar.
		if (inContainer && onDefine && /^[A-Za-z’'-]{2,}$/.test(text)) {
			const rect = sel.getRangeAt(0).getBoundingClientRect();
			onDefine(text, rect.bottom + window.scrollY, rect.left + window.scrollX + rect.width / 2);
			visible = false;
			return;
		}

		if (!inContainer || text.length < 4) {
			visible = false;
			return;
		}
		selectedText = text;
		segments = segmentsFromSelection(container, sel);
		const rect = sel.getRangeAt(0).getBoundingClientRect();
		top = rect.top + window.scrollY - 8;
		left = rect.left + window.scrollX + rect.width / 2;
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
		padding: 0.25rem;
		border-radius: var(--radius-sm);
		background: var(--surface);
		border: 1px solid var(--border);
		box-shadow: 0 6px 20px rgb(0 0 0 / 0.25);
		white-space: nowrap;
	}
	.selbar-btn {
		padding: 0.35rem 0.6rem;
		border-radius: 6px;
		font-size: 0.85rem;
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
