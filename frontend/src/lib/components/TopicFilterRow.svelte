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
		{#each topics as tc (tc.slug)}
			<button
				class="chip"
				class:active={selected === tc.slug}
				onclick={() => onSelect(selected === tc.slug ? '' : tc.slug)}
				aria-pressed={selected === tc.slug}
			>
				{tc.title}
			</button>
		{/each}
	</div>
{/if}
