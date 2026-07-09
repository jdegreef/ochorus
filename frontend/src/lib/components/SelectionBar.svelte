<script lang="ts">
	import { i18n } from '$lib/i18n.svelte';
	import { segmentsFromSelection } from '$lib/rangeMarks';
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
		isHighlighted
	}: {
		container: HTMLElement | undefined;
		cite: Cite;
		onHighlight?: (segments: Segment[]) => void;
		onNote?: (segments: Segment[]) => void;
		isHighlighted?: (segments: Segment[]) => boolean;
	} = $props();
	const t = i18n.t;

	let visible = $state(false);
	let top = $state(0);
	let left = $state(0);
	let selectedText = $state('');
	let segments = $state<Segment[]>([]);
	let copied = $state(false);

	function attribution(): string {
		const where = cite.chapter ? `${cite.book}, ${cite.chapter}` : cite.book;
		return `“${selectedText}”\n— ${cite.author}, ${where}\n${cite.url}`;
	}

	function update() {
		const sel = window.getSelection();
		const text = sel?.toString().trim() ?? '';
		if (
			!sel ||
			sel.rangeCount === 0 ||
			text.length < 4 ||
			!container ||
			!container.contains(sel.anchorNode) ||
			!container.contains(sel.focusNode)
		) {
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

	const highlighted = $derived(
		isHighlighted && segments.length > 0 ? isHighlighted(segments) : false
	);
</script>

<svelte:document onselectionchange={update} />

{#if visible}
	<div
		class="selbar"
		style="top: {top}px; left: {left}px"
		role="toolbar"
		aria-label="Selection actions"
	>
		<button class="selbar-btn" onclick={copy}>
			{copied ? '✓ ' : ''}{t('reader.copyQuote')}
		</button>
		<span class="selbar-sep"></span>
		<button class="selbar-btn" onclick={share}>{t('reader.share')}</button>
		{#if onHighlight && segments.length > 0}
			<span class="selbar-sep"></span>
			<button
				class="selbar-btn"
				class:on={highlighted}
				onclick={() => {
					onHighlight(segments);
					window.getSelection()?.removeAllRanges();
					visible = false;
				}}
				aria-pressed={highlighted}>{t('reader.highlight')}</button
			>
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
	.selbar-btn.on {
		color: var(--gold);
	}
	.selbar-sep {
		width: 1px;
		align-self: stretch;
		background: var(--border);
	}
</style>
