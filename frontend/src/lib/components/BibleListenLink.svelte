<script lang="ts">
	import type { BookSummary } from '$lib/library-public';
	import { i18n } from '$lib/i18n.svelte';
	import { localizeHref } from '$lib/href';
	import { chapterPath } from '$lib/editionHref';
	import { listen } from '$lib/listen.svelte';
	import { requestBookListen } from '$lib/listenBook';
	import Icon from '$lib/components/Icon.svelte';

	/**
	 * "Listen to the whole book" for one book of the Bible, as a headphones
	 * button on the /bible hub (its list rows and its covers), the book page's
	 * own action a tap sooner: its first chapter opens already reading aloud and
	 * the reader carries it on ($lib/listenBook). A plain link to that chapter
	 * without script, or opened in a new tab. Only where this browser can read
	 * aloud at all.
	 */
	let { book }: { book: BookSummary } = $props();
	const t = i18n.t;
</script>

{#if listen.offered}
	<a
		class="bible-listen"
		href={localizeHref(chapterPath(book.slug, 1, book.has_modern_edition))}
		aria-label="{t('bible.listenBook')}: {book.title}"
		title={t('bible.listenBook')}
		onclick={(e) => {
			if (e.button === 0 && !(e.metaKey || e.ctrlKey || e.shiftKey || e.altKey))
				requestBookListen(book.slug, 1);
		}}><Icon name="headphones" size={18} /></a
	>
{/if}

<style>
	.bible-listen {
		display: inline-grid;
		flex: none;
		place-items: center;
		width: 2.75rem;
		height: 2.75rem;
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		background: var(--surface);
		color: var(--muted);
	}
	.bible-listen:hover {
		border-color: var(--accent);
		color: var(--accent);
	}
</style>
