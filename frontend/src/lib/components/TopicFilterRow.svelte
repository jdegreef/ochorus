<script lang="ts">
	import { i18n } from '$lib/i18n.svelte';

	/**
	 * The in-place topic filter for a shelf: an "All topics" chip plus one toggle
	 * chip per topic present, bound to the shelf's `topic` URL filter. Extracted
	 * from BooksShelf and the Sermons shelf, which rendered it byte-for-byte the
	 * same — a shelf filter, distinct from TopicChips (the "Browse by topic"
	 * anchor-link section that navigates to /topics/<slug>).
	 *
	 * Shown only when the shelf spans more than one topic — a single-topic shelf
	 * has nothing to filter, so the guard lives here rather than at each call site.
	 *
	 * From sm up the chips wrap, and the Books shelf's 33 topics wrapped to four
	 * rows between the toolbar and the grid. So beyond COLLAPSE_AT the extra chips
	 * sit behind a "Show N more" chip (a selected one always stays visible). On a
	 * phone the row already scrolls sideways (.chip-scroller), so every chip is
	 * shown there and the toggle is hidden.
	 */
	let {
		topics,
		selected,
		onSelect
	}: {
		topics: { slug: string; title: string }[];
		/** The currently-selected topic slug; `''` means "All topics". */
		selected: string;
		/** Called with the new selection — `''` to clear, or a topic slug. */
		onSelect: (topic: string) => void;
	} = $props();

	const t = i18n.t;
	const COLLAPSE_AT = 6;
	let expanded = $state(false);
	const extra = $derived(Math.max(0, topics.length - COLLAPSE_AT));
</script>

{#if topics.length > 1}
	<div class="chip-scroller mb-6" aria-label={t('books.filterTopic')} role="group">
		<span class="eyebrow text-muted me-1">{t('common.topics')}</span>
		<button
			class="chip"
			class:active={selected === ''}
			onclick={() => onSelect('')}
			aria-pressed={selected === ''}
		>
			{t('books.topicAll')}
		</button>
		{#each topics as tc, i (tc.slug)}
			<button
				class="chip"
				class:topic-extra={!expanded && i >= COLLAPSE_AT && selected !== tc.slug}
				class:active={selected === tc.slug}
				onclick={() => onSelect(selected === tc.slug ? '' : tc.slug)}
				aria-pressed={selected === tc.slug}
			>
				{tc.title}
			</button>
		{/each}
		{#if extra}
			<button
				class="chip topic-toggle"
				aria-expanded={expanded}
				onclick={() => (expanded = !expanded)}
			>
				{expanded ? t('search.showLess') : t('bios.showMore').replace('%n%', String(extra))}
			</button>
		{/if}
	</div>
{/if}

<style>
	/* From sm up (where the chips wrap): collapsed extras are hidden and the
	   toggle is shown. On a phone the row scrolls, so all chips show and the
	   toggle is not needed. */
	.topic-toggle {
		display: none;
		border-style: dashed;
	}
	@media (min-width: 640px) {
		.topic-extra {
			display: none;
		}
		.topic-toggle {
			display: inline-flex;
		}
	}
</style>
